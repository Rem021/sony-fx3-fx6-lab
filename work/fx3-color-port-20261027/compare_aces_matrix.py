#!/usr/bin/env python3
"""Offline comparison using numeric data already read from primary sources."""
import json
from extract_color_tables import HERE


def inverse(m):
    a = [row[:] + [float(i == j) for j in range(3)] for i, row in enumerate(m)]
    for i in range(3):
        k = max(range(i, 3), key=lambda k: abs(a[k][i]))
        a[k], a[i] = a[i], a[k]
        d = a[i][i]
        a[i] = [x/d for x in a[i]]
        for k in range(3):
            if k != i:
                d = a[k][i]
                a[k] = [x-d*y for x, y in zip(a[k], a[i])]
    return [row[3:] for row in a]


def multiply(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rgb_xyz(p):
    m = [[p[c][0]/p[c][1] for c in range(3)], [1., 1., 1.],
         [(1-p[c][0]-p[c][1])/p[c][1] for c in range(3)]]
    wx, wy = p[3]
    white = [wx/wy, 1., (1-wx-wy)/wy]
    inv = inverse(m)
    scale = [sum(inv[i][j]*white[j] for j in range(3)) for i in range(3)]
    return [[m[i][j]*scale[j] for j in range(3)] for i in range(3)]


def main():
    inputs = json.loads((HERE / 'primary-matrix-inputs.json').read_text())
    primaries = inputs['primaries']
    ap0_to_ap1 = multiply(inverse(rgb_xyz(primaries['AP1'])), rgb_xyz(primaries['AP0']))
    # The XML/CTL convention differs: mult_f3_f33 is a row-vector multiplication.
    recovered = json.loads((HERE / 'extraction-results.json').read_text())['matrix']['coefficients']
    cases = {}
    for name in ['sony', 'venice']:
        sg3_to_ap0 = inputs['sg3_to_ap0_column_vector'][name]
        expected = multiply(ap0_to_ap1, sg3_to_ap0)
        errors = [[(recovered[r][c]-expected[r][c])*65536 for c in range(3)] for r in range(3)]
        cases[name] = dict(sg3_to_ap0=sg3_to_ap0, expected_ap1=expected,
                           differences_q16_units=errors,
                           maximum_absolute_q16_difference=max(abs(x) for row in errors for x in row))
    assert cases['venice']['maximum_absolute_q16_difference'] < 0.5
    assert cases['sony']['maximum_absolute_q16_difference'] > 1000
    assert [[round(x*65536) for x in row] for row in cases['venice']['expected_ap1']] == json.loads((HERE/'extraction-results.json').read_text())['matrix']['signed_q16']
    result = dict(source_receipts=inputs['sources'], primaries=primaries,
                  AP0_to_AP1=ap0_to_ap1, recovered_matrix=recovered, comparisons=cases,
                  nine_coefficients_equal_after_Q16_rounding=True,
                  scope='Published Sony vendor input matrix plus Academy AP0-to-AP1 math. Does not identify sensor calibration or prove hardware application.')
    (HERE / 'aces-matrix-comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(cases, indent=2))


if __name__ == '__main__':
    main()
