"""Use saved static-derived data, without replaying original ELF audit."""
from pathlib import Path
from hashlib import sha256
import json
H=Path(__file__).resolve().parent
report=json.loads((H/'original-service-descriptors-and-identity.json').read_text())
text='/* Derived default wire layouts, not captured device bytes. */\n#include <stdint.h>\n'
for row in report['speed_tables']:
    speed=row['speed'];data=(H/('derived-'+speed+'-config.bin')).read_bytes()
    assert sha256(data).hexdigest()==row['derived_wire_sha256']
    text+='static const uint8_t fx3_derived_'+speed+'['+str(len(data))+']={'+','.join(hex(v)for v in data)+'};\n'
with(H/'derived_profile_fixture.h').open('x')as f:f.write(text)
