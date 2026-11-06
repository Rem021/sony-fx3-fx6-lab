#include "veneer.hpp"
#include "callback_map.hpp"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <utility>

namespace fx6bridge {
namespace {
uint16_t u16(const uint8_t* p) {
    return static_cast<uint16_t>(p[0] | (static_cast<uint16_t>(p[1]) << 8));
}
uint32_t u32(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
           (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}
uint64_t u64(const uint8_t* p) { return static_cast<uint64_t>(u32(p)) | (static_cast<uint64_t>(u32(p+4)) << 32); }
void put16(uint8_t* p, uint16_t v) { p[0] = static_cast<uint8_t>(v); p[1] = static_cast<uint8_t>(v >> 8); }
void put32(uint8_t* p, uint32_t v) {
    for (unsigned i = 0; i < 4; ++i) p[i] = static_cast<uint8_t>(v >> (8 * i));
}
void put64(uint8_t* p, uint64_t v) {
    put32(p, static_cast<uint32_t>(v)); put32(p+4, static_cast<uint32_t>(v >> 32));
}

[[noreturn]] void unsupported_entry(size_t slot) {
    // No event pointer, nested field or source callback is dereferenced.
    std::fprintf(stderr, "FX6_BRIDGE_UNSUPPORTED_CALLBACK_SLOT=%zu\n", slot);
    std::fflush(stderr);
    std::_Exit(86);
}
template<size_t N> [[noreturn]] void diagnostic_thunk() { unsupported_entry(N); }
template<size_t... N> std::array<uint64_t, sizeof...(N)> addresses(std::index_sequence<N...>) {
    return {static_cast<uint64_t>(reinterpret_cast<uintptr_t>(&diagnostic_thunk<N>))...};
}
} // namespace

std::array<uint64_t, kCommonCount> diagnostic_thunk_addresses() {
    return addresses(std::make_index_sequence<kCommonCount>{});
}

Error prepare(const uint8_t* raw, size_t len,
              const std::array<uint64_t, kCommonCount>& thunks, Plan& out) {
    out = Plan{}; // A failed reprepare cannot leave a stale callable plan.
    if (!raw || len != kSourceSize) return Error::BadLength;
    const uint32_t count = u32(raw + 0x268);
    if (count < 1 || count > 4) return Error::BadCount;
    Plan plan;
    plan.count = count;
    for (size_t i = 0; i < 4; ++i) plan.source_slots[i] = u32(raw + 0x26c + 4*i);
    for (size_t i = 0; i < count; ++i) {
        if (plan.source_slots[i] == 0xffff) return Error::ActiveSentinel;
        for (size_t j = 0; j < i; ++j)
            if (plan.source_slots[i] == plan.source_slots[j]) return Error::DuplicateActiveSlot;
    }
    plan.original_u16 = u16(raw + 0x28a);
    if (plan.original_u16 != 1440) return Error::SourceU16Unexpected;
    plan.provisional_fx3_xavcs_u16 = 780;
    std::copy(raw, raw + 8, plan.mapped.begin());
    for (size_t i = 0; i < kCommonCount; ++i) {
        const auto& row = kCommon[i];
        const uint64_t source = u64(raw + row.src);
        plan.original_common[i] = source;
        if (source) {
            if (!thunks[i]) return Error::MissingThunk;
            if (thunks[i] == source) return Error::OriginalPointerPassThrough;
            plan.bound_thunks[i] = thunks[i];
            put64(plan.mapped.data() + row.dst, thunks[i]);
        }
        // A source-null slot remains null; never clear a non-null source.
    }
    for (size_t i = 0; i < kExtraCount; ++i) {
        plan.original_extra[i] = u64(raw + kExtra[i]);
        if (plan.original_extra[i]) ++plan.nonnull_extra;
    }
    put32(plan.mapped.data() + 0x1d0, count);
    std::copy(raw + 0x26c, raw + 0x27c, plan.mapped.begin() + 0x1d4);
    std::copy(raw + 0x27c, raw + 0x28a, plan.mapped.begin() + 0x1e4);
    put16(plan.mapped.data() + 0x1f2, plan.provisional_fx3_xavcs_u16);
    std::copy(raw + 0x28c, raw + 0x290, plan.mapped.begin() + 0x1f4);
    plan.prepared = true;
    out = plan;
    return Error::None;
}

Error install_before_init(const Plan& plan, Registry& registry) {
    if (!plan.prepared) return Error::NotPrepared;
    if (registry.installed) return Error::AlreadyCalled;
    registry.original_common = plan.original_common;
    registry.bound_thunks = plan.bound_thunks;
    registry.installed = true;
    return Error::None;
}

CallResult call_original_once(Plan& plan, const Registry& registry,
                              const RuntimeGates& gates, OriginalFx3Init original) {
    if (!plan.prepared) return {Error::NotPrepared, false, 0};
    if (plan.called) return {Error::AlreadyCalled, false, 0};
    if (!registry.installed || registry.original_common != plan.original_common ||
        registry.bound_thunks != plan.bound_thunks)
        return {Error::RegistryNotInstalled, false, 0};
    if (!original || !gates.source_elf_identity || !gates.original_fx3_mpr_identity ||
        !gates.unknown_entry_stop_armed || !gates.first_threshold_consumer_stop_armed ||
        !gates.writer_mode_branch_stop_armed ||
        (plan.nonnull_extra && !gates.extra_api_stop_armed))
        return {Error::RuntimeGateMissing, false, 0};
    plan.called = true; // Set before call: synchronous/asynchronous callbacks may start inside Init.
    const int32_t rc = original(plan.mapped.data());
    plan.original_return = rc;
    plan.original_return_known = true;
    return {Error::None, true, rc};
}

Error classify_writer_branch(WriterBranch branch, bool original_fx6_branch_verified,
                             bool first_threshold_consumer_not_yet_executed) {
    if (!original_fx6_branch_verified || !first_threshold_consumer_not_yet_executed ||
        branch == WriterBranch::Unknown)
        return Error::WriterBranchUnknown;
    if (branch == WriterBranch::Fx6MxfObserved) return Error::MxfUnsupported;
    return Error::None; // A symbolic branch classification, not recording permission.
}

Error guard_writer_branch(const Plan& plan, WriterBranch branch,
                          bool original_fx6_branch_verified,
                          bool first_threshold_consumer_not_yet_executed) {
    if (!plan.prepared || !plan.called || !plan.original_return_known)
        return Error::WriterBranchUnknown;
    if (plan.original_return != 0) return Error::OriginalInitFailed;
    return classify_writer_branch(branch, original_fx6_branch_verified,
                                  first_threshold_consumer_not_yet_executed);
}

Error translate_poweron_12(const uint8_t* source, size_t len,
                            bool live_waiter, bool unique_key,
                            bool fx3_dispatcher_owns_source,
                            std::array<uint8_t, 12>& target) {
    if (!source || len != 12 || !live_waiter || !unique_key || !fx3_dispatcher_owns_source ||
        u32(source) != 0x1026 || u32(source + 8) != 0)
        return Error::PowerOnContractMismatch;
    std::copy(source, source + 12, target.begin());
    put32(target.data(), 0x102d); // Echo at +4 and original result 0 at +8 remain unchanged.
    return Error::None;
}

} // namespace fx6bridge
