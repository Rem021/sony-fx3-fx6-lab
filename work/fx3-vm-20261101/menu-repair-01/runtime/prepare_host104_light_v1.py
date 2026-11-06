from pathlib import Path
import ast
R=Path(__file__).resolve().parent;p=R/'run_candidate104_light_v1.py';assert not p.exists();s=(R/'run_candidate104_v3.py').read_text().replace('gate_input104_v3','gate_input104_light_v1').replace('restore_api103_v1','restore_api103_v2');s=s.replace(",'gdb_sysregs104_v2.py'",'')
needle="    if candidate['ap104_contract']['authority']!='msg_b94a0dacc3e4':raise RuntimeError('Missing AP104 passive-only authority')\n";assert s.count(needle)==1;s=s.replace(needle,needle+"    if candidate.get('ap104_light_contract',{}).get('authority')!='msg_b27db37f09d2':raise RuntimeError('Missing AP104-light authority')\n")
needle="                uipc104=re.search";assert s.count(needle)==1;s=s.replace(needle,"                if 'unfetched'in serial_now or re.search(r'FX3_LIGHT104_ALLOC_RETURN[^\\n]*result=-1018(?: |$)',serial_now):\n                    early_stop_reason='AP104-light first observed native unfetched/alloc -1018; stop promptly; later guest calls may precede host UART observation';break\n"+needle)
ast.parse(s);p.write_text(s);print(p)
