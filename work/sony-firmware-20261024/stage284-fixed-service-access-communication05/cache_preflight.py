"""Pure preflight decision. No query, media access, unmount or launch API."""
def validate(observed,target,physical_port):
    if observed.get('candidate_count')!=1 or len(observed.get('candidates',[]))!=1:raise ValueError('unique current camera cache required')
    candidate=observed['candidates'][0]
    if any(candidate.get(k)!=target[k]for k in ['VID','PID','locationID','registryID','model']):raise ValueError('fixed target changed')
    if type(physical_port)is not int or physical_port<=0 or candidate.get('physical_port_registryID')!=physical_port:raise ValueError('physical USB-C anchor required')
    if observed.get('media_unknown')is not False or observed.get('mounted_camera_media')!=[] or not observed.get('storage_driver_classes'):
        raise ValueError('camera volumes not known unmounted or no storage driver')
    # Finder eject may remove every IOMedia node while USB/MSC remains present.
    # Zero cached media is valid, provided metadata is complete and no mount exists.
    if not isinstance(observed.get('cached_media_BSD_names'),list):raise ValueError('missing media metadata')
    return True
