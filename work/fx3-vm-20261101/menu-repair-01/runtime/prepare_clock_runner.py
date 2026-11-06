from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'run_surface_candidate.py';s=p.read_text();s=s.replace("    ap.add_argument('--label', default='guest')", "    ap.add_argument('--label', default='guest')\n    ap.add_argument('--icount-shift', type=int, choices=[0,1], default=None)")
s=s.replace("for name in ['run_surface_candidate.py', 'cpio_audit.py', 'decode_printk_ring.py']:", "for name in [Path(__file__).name, 'cpio_audit.py', 'decode_printk_ring.py']:")
s=s.replace('    if ns.trace_seconds:\n        args +=', "    if ns.icount_shift is not None:\n        args += ['-icount', f'shift={ns.icount_shift},align=off,sleep=off']\n    if ns.trace_seconds:\n        args +=")
s=s.replace("'seconds': ns.seconds, 'trace_prefix_seconds': ns.trace_seconds,", "'seconds': ns.seconds, 'icount_profile': None if ns.icount_shift is None else f'shift={ns.icount_shift},align=off,sleep=off', 'trace_prefix_seconds': ns.trace_seconds,")
s=s.replace("str(ROOT / 'run_surface_candidate.py')", "str(Path(__file__))")
s=s.replace("'--label', label]}})", "'--label', label]+(['--icount-shift',str(ns.icount_shift)] if ns.icount_shift is not None else [])}})")
s=s.replace('            tracing = ns.trace_seconds > 0', '            tracing = ns.trace_seconds > 0\n            first_draw_captured = False')
needle='                time.sleep(.25)'
extra=r'''
                if not first_draw_captured:
                    live_serial=(run/'serial.log').read_text(errors='replace')
                    draw_lines=[line for line in live_serial.split('\n') if 'FX3_GPE_CMD ' in line and 'result=0 ' in line and ('op=FillRect ' in line or 'op=BitBlit ' in line)]
                    if draw_lines:
                        qmp('stop')
                        target=run/'osd-first-draw.raw'
                        qmp('human-monitor-command', {'command-line':'pmemsave 0x43feb5100 0x12c000 "'+str(target)+'"'})
                        if target.exists():
                            import importlib.util
                            spec=importlib.util.spec_from_file_location('osd_decoder',ROOT.parents[1]/'lead-claude/audits/vdf0147-plane-scanout/dump_osd_frame.py')
                            decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
                            renders=[]
                            for fmt in ['format0-le16','format1-le32']:
                                cfg={'dump_base':'0x43feb5100','width':640,'height':480,'planes':[{'address':'0x43feb5100','width':640,'height':480,'stride_pixels':640,'format':fmt,'component_order':'RGBA','alpha_mode':'opaque','global_alpha':255,'x':0,'y':0,'z':0}]}
                                name='osd-first-'+fmt+'-RGBA-opaque'
                                (run/(name+'.json')).write_text(json.dumps(cfg,indent=2)+'\n')
                                w,h,pixels=decoder.render(target.read_bytes(),cfg)
                                png=run/(name+'.png');png.write_bytes(decoder.png_bytes(w,h,pixels))
                                renders.append({'path':str(png),'sha256':digest(png),'assumptions':cfg,'nonuniform_pixels':len({pixels[i:i+4] for i in range(0,len(pixels),4)})>1})
                            (run/'osd-first-draw.json').write_text(json.dumps({'first_draw':draw_lines[0],'physical_readback':True,'readback_sha256':digest(target),'renders':renders,'menu_acceptance':False},indent=2)+'\n')
                        first_draw_captured=True
                        qmp('cont')
                time.sleep(.25)'''
assert needle in s;s=s.replace(needle,extra);(R/'run_clock_candidate.py').write_text(s)
