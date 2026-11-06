#include "veneer.hpp"
#include "callback_map.hpp"

#include <array>
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

using namespace fx6bridge;

static int calls = 0;
static const Registry* installed = nullptr;
static const Plan* planned = nullptr;

static uint16_t u16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
static uint32_t u32(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
           (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}
static uint64_t u64(const uint8_t* p) { return u32(p) | (static_cast<uint64_t>(u32(p+4)) << 32); }
static void put32(uint8_t* p, uint32_t v) { for (int i=0; i<4; ++i) p[i]=static_cast<uint8_t>(v>>(8*i)); }

// Host fixture only: returns nonzero 3, never simulates Sony Init success.
static int32_t original_probe(const uint8_t* mapped) {
    assert(installed && installed->installed && planned && planned->called);
    assert(mapped == planned->mapped.data());
    assert(u32(mapped + 0x1d0) == 2 && u16(mapped + 0x1f2) == 780);
    ++calls;
    return 3;
}

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--trigger-unsupported") {
        auto thunks = diagnostic_thunk_addresses();
        reinterpret_cast<void(*)()>(static_cast<uintptr_t>(thunks[0]))();
        return 99; // unreachable
    }
    assert(argc == 2);
    std::ifstream input(argv[1], std::ios::binary);
    assert(input.good());
    std::vector<uint8_t> raw(std::istreambuf_iterator<char>{input}, {});
    assert(raw.size() == kSourceSize);
    auto thunks = diagnostic_thunk_addresses();
    for (size_t i=0; i<thunks.size(); ++i) {
        assert(thunks[i] != 0);
        for (size_t j=0; j<i; ++j) assert(thunks[i] != thunks[j]);
    }
    Plan p;
    assert(prepare(raw.data(), raw.size(), thunks, p) == Error::None);
    assert(p.count == 2 && p.source_slots == (std::array<uint32_t,4>{0x1000,0x1010,0,0}));
    assert(p.original_u16 == 1440 && p.provisional_fx3_xavcs_u16 == 780);
    assert(u32(p.mapped.data()+0x1d0) == 2);
    assert(u32(p.mapped.data()+0x1d4) == 0x1000 && u32(p.mapped.data()+0x1d8) == 0x1010);
    assert(u32(p.mapped.data()+0x1dc) == 0 && u32(p.mapped.data()+0x1e0) == 0);
    assert(p.nonnull_extra == 10);
    unsigned common_nonnull = 0;
    for (size_t i=0; i<kCommonCount; ++i) {
        auto v = u64(raw.data()+kCommon[i].src);
        assert(p.original_common[i] == v);
        assert(u64(p.mapped.data()+kCommon[i].dst) == (v ? thunks[i] : 0));
        if (v) { ++common_nonnull; assert(thunks[i] != v); }
    }
    assert(common_nonnull == 46);
    assert(prepare(raw.data(), raw.size()-1, thunks, p) == Error::BadLength);
    assert(!p.prepared);
    auto modified = raw;
    put32(modified.data()+0x268, 5);
    assert(prepare(modified.data(), modified.size(), thunks, p) == Error::BadCount);
    modified = raw; put32(modified.data()+0x26c, 0xffff);
    assert(prepare(modified.data(), modified.size(), thunks, p) == Error::ActiveSentinel);
    modified = raw; put32(modified.data()+0x270, 0x1000);
    assert(prepare(modified.data(), modified.size(), thunks, p) == Error::DuplicateActiveSlot);
    modified = raw; modified[0x28a] = 0;
    assert(prepare(modified.data(), modified.size(), thunks, p) == Error::SourceU16Unexpected);
    auto broken = thunks;
    broken[0] = 0;
    assert(prepare(raw.data(), raw.size(), broken, p) == Error::MissingThunk);
    broken = thunks; broken[0] = u64(raw.data()+kCommon[0].src);
    assert(prepare(raw.data(), raw.size(), broken, p) == Error::OriginalPointerPassThrough);
    assert(prepare(raw.data(), raw.size(), thunks, p) == Error::None);
    Registry registry;
    RuntimeGates gates;
    assert(call_original_once(p, registry, gates, original_probe).error == Error::RegistryNotInstalled);
    assert(install_before_init(p, registry) == Error::None);
    assert(install_before_init(p, registry) == Error::AlreadyCalled);
    assert(call_original_once(p, registry, gates, original_probe).error == Error::RuntimeGateMissing);
    assert(calls == 0 && !p.called);
    gates = {true,true,true,true,true,true};
    installed = &registry; planned = &p;
    auto result = call_original_once(p, registry, gates, original_probe);
    assert(result.error == Error::None && result.original_called && result.original_return == 3 && calls == 1);
    assert(call_original_once(p, registry, gates, original_probe).error == Error::AlreadyCalled && calls == 1);
    assert(p.original_return_known && p.original_return == 3);
    assert(guard_writer_branch(p, WriterBranch::Fx6XavcsObserved, true, true) == Error::OriginalInitFailed);
    assert(classify_writer_branch(WriterBranch::Unknown, true, true) == Error::WriterBranchUnknown);
    assert(classify_writer_branch(WriterBranch::Fx6MxfObserved, true, true) == Error::MxfUnsupported);
    assert(classify_writer_branch(WriterBranch::Fx6XavcsObserved, false, true) == Error::WriterBranchUnknown);
    assert(classify_writer_branch(WriterBranch::Fx6XavcsObserved, true, false) == Error::WriterBranchUnknown);
    assert(classify_writer_branch(WriterBranch::Fx6XavcsObserved, true, true) == Error::None);
    uint8_t poweron[12]{};
    put32(poweron, 0x1026); put32(poweron+4, 0x12345678);
    std::array<uint8_t,12> converted{};
    assert(translate_poweron_12(poweron,12,true,true,true,converted) == Error::None);
    assert(u32(converted.data()) == 0x102d && u32(converted.data()+4) == 0x12345678 && u32(converted.data()+8) == 0);
    assert(translate_poweron_12(poweron,12,false,true,true,converted) == Error::PowerOnContractMismatch);
    put32(poweron+8,1);
    assert(translate_poweron_12(poweron,12,true,true,true,converted) == Error::PowerOnContractMismatch);
    std::puts("host veneer: mapping, unique nonzero original call, provisional 780, post-choice gate, PowerOn bytes and rejection fixtures passed");
}
