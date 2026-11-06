#ifndef FX3_GPE_BACKEND_V5_H
#define FX3_GPE_BACKEND_V5_H
#include <stddef.h>
#include <stdint.h>
#define GPE_EXTENTS 64
#define GPE_EVENTS 128
#define GPE_BATCHES 64
#define GPE_MAX_ROWS 65536
/* Backend errors, deliberately not claimed to be Sony's numeric ABI. */
enum gpe_status { GPE_OK, GPE_INVALID, GPE_UNSUPPORTED, GPE_BOUNDS,
 GPE_STALE, GPE_BUSY, GPE_CAPACITY, GPE_OVERLAP, GPE_DELIVERY, GPE_EMPTY };
struct gpe_ref { uint64_t handle, generation; };
struct gpe_extent { struct gpe_ref ref; uint64_t physical_base; uint8_t *cpu;
 size_t bytes; uint32_t leases; unsigned active, retiring; };
struct gpe_lease { struct gpe_ref ref; unsigned slot, held; };
struct gpe_callback_info { uint32_t sequence, completion_source; uint64_t function, argument; };
struct gpe_callback_param { uint32_t sequence, zero; uint64_t argument; };
struct gpe_plan { uint64_t dst, src, dst_step, src_step, line; uint32_t rows, pixel, bpp;
 unsigned blit, approx_blend, constant_alpha, flip_h, flip_v;
 uint64_t src_line; uint32_t src_rows, src_bpp, source_width, target_width, target_height;
 uint32_t offset_x, offset_y, write_width; unsigned approx_fmt2, approx_stretch; /* stretch:1 nearest_v1 edge;2 nearest_v2 pixel-center */
 uint8_t color[4]; };
struct gpe_batch { uint64_t id, commands, failures, delivery_failures; uint32_t first_sequence; int first_error; };
struct gpe_event { struct gpe_callback_info info; int status; struct gpe_lease dst, src; };
/* Hooks return 0 on success. They receive exact little-endian wire bytes.
 * Callback hook resolves a trusted guest function token; no raw function cast. */
struct gpe_hooks { void *user;
 int (*callback)(void *, uint64_t, const uint8_t [16]);
 int (*status)(void *, uint32_t, const uint8_t [4]); };
struct gpe_context { struct gpe_extent extents[GPE_EXTENTS];
 struct gpe_event events[GPE_EVENTS]; unsigned head, count, delivering;
 struct gpe_batch batches[GPE_BATCHES]; unsigned batch_count; int current;
 struct gpe_hooks hooks; };
void gpe_init(struct gpe_context *, struct gpe_hooks);
int gpe_register(struct gpe_context *, struct gpe_ref, uint64_t, void *, size_t);
/* BUSY means retirement requested; CPU storage must remain until leases==0. */
int gpe_unregister(struct gpe_context *, struct gpe_ref);
int gpe_acquire(struct gpe_context *, struct gpe_ref, struct gpe_lease *);
int gpe_release(struct gpe_context *, struct gpe_lease *);
int gpe_begin_batch(struct gpe_context *, uint64_t);
/* Pure decoders; input must point to n readable bytes. */
int gpe_plan_fill(const void *, size_t, struct gpe_plan *);
int gpe_plan_blit(const void *, size_t, struct gpe_plan *);
/* FIFO worker adapter: raw params only, not 16B message header; refs supplied
 * from allocation owner, never inferred by calling GetDmmMemInfo. */
int gpe_submit(struct gpe_context *, uint32_t opcode, uint32_t sequence,
 uint32_t completion_source, const void *, size_t, struct gpe_ref dst, struct gpe_ref src);
int gpe_deliver_one(struct gpe_context *);
#endif
