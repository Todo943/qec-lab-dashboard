#!/usr/bin/env python3
"""Audit an IQM compiled surface-code circuit saved by test.ipynb.

Usage:
  python audit_qec_compilation.py iqm_circuit_d3_Z_r3_emerald.json
  python audit_qec_compilation.py iqm_circuit_d3_Z_r3_emerald.json --couplers emerald_couplers.json

Optional --couplers JSON format:
  {"calibration_set_id": "...", "couplers": [["QB1", "QB2"], ["QB2", "QB3"], ...]}

No Qrisp, IQM token, or external packages required. This is a static circuit
analysis, NOT a hardware-execution or logical-equivalence test.
"""
import argparse
import ast
from collections import Counter
import json
from pathlib import Path


def pair(a, b):
    return tuple(sorted((str(a), str(b))))


def parse_mapping(mapping):
    data = {tuple(ast.literal_eval(k)): v for k, v in mapping['data'].items()}
    anc = {tuple(ast.literal_eval(k)): v[-1] for k, v in mapping['anc'].items()}
    if len(set(data.values()) | set(anc.values())) != len(data) + len(anc):
        raise ValueError('Mapped data/ancilla physical qubits must be unique')
    return data, anc


def audit(path, coupler_path=None):
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    instructions = obj['instructions']
    data, anc = parse_mapping(obj['qubit_map'])
    n_data, n_anc = len(data), len(anc)
    d = int(round(n_data ** .5))
    if n_data != d*d or n_anc != d*d - 1:
        raise ValueError(f'Unexpected rotated surface-code qubit counts: {n_data} + {n_anc}')

    interaction_edges = {
        pair(a_phys, d_phys)
        for a_coord, a_phys in anc.items()
        for d_coord, d_phys in data.items()
        if abs(a_coord[0] - d_coord[0]) == 1 and abs(a_coord[1] - d_coord[1]) == 1
    }
    names = Counter(op['name'].lower() for op in instructions)
    cz_edges = Counter(
        pair(*op['locus']) for op in instructions if op['name'].lower() == 'cz'
    )
    measured = sum(op['name'].lower() == 'measure' for op in instructions)
    if not cz_edges:
        raise ValueError('No CZ gates: check this circuit uses IQM native operations')

    reps = set(cz_edges.values())
    r = next(iter(reps)) if len(reps) == 1 else None
    correct_pairs = set(cz_edges) == interaction_edges
    ideal_cz_per_round = 4 * d * (d - 1)  # d=3 -> 24
    all_expected_edges = len(interaction_edges) == ideal_cz_per_round
    theoretical_cz = ideal_cz_per_round * r if r is not None else None
    # Valid for native CZ implementation of this circuit's stabilizer schedule.

    # Greedy per-qubit dependency depths. No physical durations or crosstalk modeled.
    ops_depth, twoq_depth = {}, {}
    for op in instructions:
        qubits = op['locus']
        nxt = 1 + max((ops_depth.get(q, 0) for q in qubits), default=0)
        for q in qubits:
            ops_depth[q] = nxt
        if op['name'].lower() == 'cz':
            two = 1 + max((twoq_depth.get(q, 0) for q in qubits), default=0)
            for q in qubits:
                twoq_depth[q] = two

    report = {
        'artifact': Path(path).name,
        'calibration_set_id': obj.get('calibration_set_id'),
        'code_distance_inferred': d,
        'data_qubits': n_data,
        'ancilla_qubits': n_anc,
        'physical_qubits_used': len(set(data.values()) | set(anc.values())),
        'inferred_rounds_from_CZ_multiplicities': r,
        'gate_counts': dict(names),
        'distinct_CZ_pairs': len(cz_edges),
        'expected_surface_code_CZ_pairs': len(interaction_edges),
        'expected_interaction_set_matches_CZ_pairs': correct_pairs and all_expected_edges,
        'missing_CZ_pairs': [list(p) for p in sorted(interaction_edges - set(cz_edges))],
        'unexpected_CZ_pairs': [list(p) for p in sorted(set(cz_edges) - interaction_edges)],
        'CZ_pair_multiplicities': dict(Counter(cz_edges.values())),
        'ideal_CZ_count_for_this_schedule': theoretical_cz,
        'observed_CZ_count': names.get('cz', 0),
        'CZ_overhead_vs_schedule': (names.get('cz', 0) - theoretical_cz) if theoretical_cz is not None else None,
        'explicit_swap_instructions': names.get('swap', 0),
        'dependency_depth_all_native_operations': max(ops_depth.values(), default=0),
        'dependency_depth_CZ_only': max(twoq_depth.values(), default=0),
        'expected_measurements_if_no_reset': (n_anc * r + n_data) if r is not None else None,
        'observed_measurements': measured,
        'native_gate_names_only': set(names).issubset({'prx', 'cz', 'measure'}),
    }

    if coupler_path is not None:
        native = json.loads(Path(coupler_path).read_text(encoding='utf-8'))
        edges = native['couplers'] if isinstance(native, dict) else native
        verified = {pair(*p) for p in edges}
        missing = set(cz_edges) - verified
        report['topology_check'] = {
            'provided_calibration_set_id': native.get('calibration_set_id') if isinstance(native, dict) else None,
            'calibration_id_matches': native.get('calibration_set_id') == obj.get('calibration_set_id') if isinstance(native, dict) else None,
            'all_CZ_pairs_are_available_native_couplers': not bool(missing),
            'non_native_pairs': [list(p) for p in sorted(missing)],
        }
    else:
        report['topology_check'] = 'NOT DONE: provide the hardware CZ coupler list using --couplers'

    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('circuit', help='Compiled IQM Circuit JSON saved by team notebook')
    p.add_argument('--couplers', help='Optional JSON of actual calibrated native CZ pairs')
    p.add_argument('--output', help='Optional JSON report path')
    args = p.parse_args()
    report = audit(args.circuit, args.couplers)
    output = json.dumps(report, indent=2)
    print(output)
    if args.output:
        Path(args.output).write_text(output + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
