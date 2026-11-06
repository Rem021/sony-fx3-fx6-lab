#ifndef FX3_FRAME_TARGET_V1
#define FX3_FRAME_TARGET_V1
#define FT_WORDS 10
/* version, kind(1=legacy native proc screen,2=native open object), object,
 * epoch, identity, parent physical, parent bytes, native unit token, vptr,
 * captured current FB physical. The tuple is historical after lease release. */
static int frame_tuple_valid(const U*t,U physical,U span,unsigned token){if(!t||t[0]!=1||(t[1]!=1&&t[1]!=2)||!t[3]||!t[6]||t[6]>~0UL-t[5]||t[7]!=token||t[9]!=physical||physical<t[5]||physical>=t[5]+t[6]||!span||span>t[5]+t[6]-physical)return 0;if(t[1]==2&&(!t[2]||!t[4]||!t[8]))return 0;return 1;}
#endif
