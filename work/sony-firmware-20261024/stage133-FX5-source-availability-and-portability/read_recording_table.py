#!/usr/bin/env python3
"""Expand the captured official recording table, including row/column spans."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            assert self.table is None, 'Nested table requires a separate parser'
            self.table = []
        elif self.table is not None:
            if tag == 'tr':
                self.row = []
            elif tag in ('td', 'th'):
                self.cell = {'rowspan': int(attrs.get('rowspan', '1')),
                             'colspan': int(attrs.get('colspan', '1')), 'text': []}
            elif tag == 'br' and self.cell is not None:
                self.cell['text'].append(' ')

    def handle_data(self, data):
        if self.cell is not None:
            self.cell['text'].append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.cell['text'] = re.sub(r'\s+', ' ', ''.join(self.cell['text'])).strip()
            self.row.append(self.cell)
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def expand(rows):
    grid = {}
    for row_number, cells in enumerate(rows):
        column = 0
        for cell in cells:
            while (row_number, column) in grid:
                column += 1
            for dy in range(cell['rowspan']):
                for dx in range(cell['colspan']):
                    key = row_number + dy, column + dx
                    assert key not in grid
                    grid[key] = cell['text']
            column += cell['colspan']
    return [[grid.get((y, x), '') for x in range(max(c for _, c in grid) + 1)]
            for y in range(max(r for r, _ in grid) + 1)]


def main():
    source = HERE / 'public-pages/fx5-guide-video_quality_setting.html'
    capture = json.loads((HERE / 'public-guide-captures.json').read_text())
    record = next(r for r in capture['records'] if r['name'] == 'fx5-guide-video_quality_setting')
    assert record['status'] == 200
    assert hashlib.sha256(source.read_bytes()).hexdigest() == record['sha256']
    parser = Tables()
    parser.feed(source.read_text())
    assert len(parser.tables) == 1
    grid = expand(parser.tables[0])
    rows = []
    for raw in grid:
        assert len(raw) == 6
        if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', raw[0]):
            continue
        assert raw[1].startswith('XAVC ')
        rows.append({'project_frame_rate': raw[0], 'codec': raw[1], 'video_format': raw[2],
                     'quality_Mbps': dict(zip(('High', 'Mid', 'Low'), raw[3:]))})
    assert rows
    target_rate = [r for r in rows if r['project_frame_rate'] == '29.97']
    assert any(r['codec'] == 'XAVC S-L 420' and r['video_format'] == '1920×1080P'
               and r['quality_Mbps'] == {'High': '50', 'Mid': '16', 'Low': '16'} for r in target_rate)
    hs = [r for r in rows if 'HS-L' in r['codec']]
    assert any(r['project_frame_rate'] == '59.94' and r['codec'] == 'XAVC HS-L 420'
               and r['quality_Mbps'] == {'High': '150', 'Mid': '75', 'Low': '45'} for r in hs)
    result = {'scope': 'Published FX5 v1 help-guide XAVC main-recording table only, not firmware execution',
              'source_url': record['url'], 'source_sha256': record['sha256'], 'expanded_rows': rows,
              'rows_at_29_97': target_rate, 'HS_L_rows': hs,
              'published_HS_L_1080_rows': [r for r in hs if r['video_format'] == '1920×1080P'],
              'published_HS_L_29_97_rows': [r for r in hs if r['project_frame_rate'] == '29.97'],
              'no_claim_about_hidden_modes_future_firmware_or_unlisted_hardware_capability': True,
              'proxy_HEVC_16M_not_counted_as_MAIN': True,
              'actual_FX5_or_FX3_firmware_package_or_camera_test': False}
    (HERE / 'fx5-recording-table-review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'expanded_XAVC_rows': len(rows), 'rows_at_29_97': len(target_rate), 'HS_L_rows': len(hs),
                      'HS_L_1080_rows': len(result['published_HS_L_1080_rows']),
                      'HS_L_29_97_rows': len(result['published_HS_L_29_97_rows'])}))


if __name__ == '__main__':
    main()
