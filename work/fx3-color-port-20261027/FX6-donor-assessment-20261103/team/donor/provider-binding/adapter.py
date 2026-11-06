#!/usr/bin/env python3
"""Declarative FX6 look-control to FX3 backend boundary prototype; no injection."""
import json

from analyze import BASE, ROOT


def plan(binding, *, event_kind, look, ip, provider_status, provider_word):
    """Accept only the one byte-proven common look-22 route.

    The caller must supply independently observed provider values.  This
    routine deliberately cannot allocate an AV event callback or submit DMA.
    """
    if (event_kind, look, ip) != (0, 22, 0):
        raise ValueError('unproved event kind/look/IP route')
    if provider_status <= 0 or provider_word != 0x30:
        raise ValueError('provider word does not route to look22/mode3 without override')
    fx6 = binding['models']['FX6_6.01']['look22']
    fx3 = binding['models']['FX3_7.02']['look22']
    if fx6['normalized_70_payloads_sha256'] != fx3['normalized_70_payloads_sha256']:
        raise ValueError('source descriptor payloads diverge')
    if any((a['name'], a['register_offset'], a['word_count'], a['payload_sha256']) !=
           (b['name'], b['register_offset'], b['word_count'], b['payload_sha256'])
           for a, b in zip(fx6['rows'], fx3['rows'])):
        raise ValueError('source descriptor row mismatch')
    return {
        'scope': 'offline declarative adapter, no live callback or DMA',
        'input_contract': {'provider_status': provider_status, 'provider_word': hex(provider_word),
                           'event_kind': event_kind, 'look': look, 'ip': ip},
        'fx6_original_branch': {'mode': 3, 'override_flag': 0,
                                'builder_call_offset': binding['models']['FX6_6.01']['builder_call_offset'],
                                'descriptor_va': hex(BASE + int(fx6['descriptor_array_offset'], 16))},
        'fx3_backend_boundary': {'event_fields': {'u32_at_0': 0, 'u32_at_4': 22, 'u32_at_8': 0},
                                 'builder_call_offset': binding['models']['FX3_7.02']['builder_call_offset'],
                                 'local_descriptor_va': hex(BASE + int(fx3['descriptor_array_offset'], 16)),
                                 'descriptor_count': 70,
                                 'descriptor_payload_sha256': fx3['normalized_70_payloads_sha256'],
                                 'event_callback_at_0x10': 'unbound; required before execution',
                                 'provider_registration': 'unbound; no live FX3/FX6 provider table address'},
        'not_executable_as_firmware': True,
    }


def main():
    binding = json.loads((ROOT / 'binding-evidence.json').read_text())
    positive = plan(binding, event_kind=0, look=22, ip=0,
                    provider_status=4, provider_word=0x30)
    negatives = []
    for label, kwargs in [
        ('override_word_0x31', {'provider_word': 0x31}),
        ('ip_1', {'ip': 1}),
        ('other_look', {'look': 23}),
        ('failed_provider', {'provider_status': 0}),
        ('different_event_kind', {'event_kind': 1}),
    ]:
        args = dict(event_kind=0, look=22, ip=0, provider_status=4, provider_word=0x30)
        args.update(kwargs)
        try:
            plan(binding, **args)
        except ValueError as exc:
            negatives.append({'case': label, 'rejected': True, 'reason': str(exc)})
        else:
            raise AssertionError(label)
    output = {'binding_input_sha256': __import__('hashlib').sha256(
                  (ROOT / 'binding-evidence.json').read_bytes()).hexdigest(),
              'positive': positive, 'negatives': negatives,
              'fixture_warning': '0x30 and event kind0/look22/ip0 are explicit synthetic inputs, not observed natural FX6 MAIN/monitor selection'}
    (ROOT / 'adapter-receipt.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'positive_descriptor_count': 70,
                      'same_payloads_sha256': positive['fx3_backend_boundary']['descriptor_payload_sha256'],
                      'negative_cases': len(negatives), 'live_binding': False}))


if __name__ == '__main__':
    main()
