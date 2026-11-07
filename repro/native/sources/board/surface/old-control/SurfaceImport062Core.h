/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#define SURFACE062_BASE UINT64_C(0x180000000)
#define SURFACE062_SITE UINT64_C(0x1841704ac)
#define SURFACE062_SW_VPTR UINT64_C(0x1ee1c22e8)
#define SURFACE062_SW_IMPORT UINT64_C(0x1841077f8)
#define SURFACE062_TOP UINT64_C(0x1000000000000)
#define SURFACE062_IMMEDIATE UINT32_C(0x6200)
#define SURFACE062_TRAP (UINT32_C(0xd4200000) | (SURFACE062_IMMEDIATE << 5))
#define SURFACE062_SCAN_LIMIT 4096U

enum surface062_reason {
    SURFACE062_PASS = 0, SURFACE062_NIL, SURFACE062_OTHER_BACKEND,
    SURFACE062_REPAIRED, SURFACE062_ALREADY_TRACKED, SURFACE062_INVALID,
    SURFACE062_READ_FAILED, SURFACE062_FOREIGN_LINK, SURFACE062_SCAN_LIMIT_REACHED,
    SURFACE062_STATE_CHANGED, SURFACE062_WRITE_FAILED, SURFACE062_ROLLBACK_FAILED,
    SURFACE062_COMMITTED_UNVERIFIED
};

typedef int (*surface062_read_fn)(void *, uint64_t, void *, size_t);
typedef int (*surface062_write_fn)(void *, uint64_t, const void *, size_t);
struct surface062_io {void *opaque; surface062_read_fn read; surface062_write_fn write;};
struct surface062_result {
    enum surface062_reason reason;
    uint64_t context, surface, vptr, import, head_address, head, next, owner;
    uint32_t references, flags, state_flags, nodes;
    bool committed, verified;
};

static inline bool surface062_pointer(uint64_t p, size_t bytes)
{
    return p >= 4096 && !(p & 7) && bytes <= SURFACE062_TOP && p < SURFACE062_TOP - bytes;
}

static inline bool surface062_match(uint64_t cache, uint64_t pc, uint32_t immediate, uint32_t word)
{
    return cache >= SURFACE062_BASE && cache - SURFACE062_BASE <= UINT64_C(0x100000000) &&
        pc == cache + (SURFACE062_SITE - SURFACE062_BASE) && immediate == SURFACE062_IMMEDIATE &&
        word == SURFACE062_TRAP;
}

/* Replay only the original MOV x23,x0. All other GPRs, SIMD, SP, LR and NZCV remain untouched. */
static inline void surface062_replay(uint64_t registers[29], uint64_t *pc)
{
    registers[23] = registers[0];
    *pc += 4;
}

static inline int surface062_read64(const struct surface062_io *io, uint64_t address, uint64_t *value)
{
    return !surface062_pointer(address, sizeof(*value)) ? -1 : io->read(io->opaque, address, value, sizeof(*value));
}

static inline int surface062_read32(const struct surface062_io *io, uint64_t address, uint32_t *value)
{
    return address < 4096 || (address & 3) || address >= SURFACE062_TOP - 4 ? -1 :
        io->read(io->opaque, address, value, sizeof(*value));
}

/* Return 1 for a member, 0 for a complete miss, -1 for unreadable/invalid nodes, -2 for a bounded-out chain.
 * This is not a guessed GPU object capacity: the bound only prevents an untrusted cyclic list from monopolizing EL1. */
static inline int surface062_find(const struct surface062_io *io, uint64_t head, uint64_t wanted, uint32_t *nodes)
{
    uint64_t cursor = head;
    for (unsigned i = 0; cursor && i < SURFACE062_SCAN_LIMIT; ++i) {
        ++*nodes;
        if (!surface062_pointer(cursor, 0xc8)) return -1;
        if (cursor == wanted) return 1;
        if (surface062_read64(io, cursor + 0x10, &cursor)) return -1;
    }
    return cursor ? -2 : 0;
}

/* Exact missing track_surface semantics at the software-import return, not a generic assertion bypass.
 * Context lists are caller-serialized, as in the original track_surface implementation.
 * Only freshly imported SW wrappers with the verified 23F84 layout may be inserted. */
static inline struct surface062_result surface062_repair(const struct surface062_io *io,
    bool enabled, bool backboardd, uint64_t cache, uint64_t context, uint64_t surface)
{
    struct surface062_result r = {.reason = SURFACE062_PASS, .context = context, .surface = surface};
    if (!enabled || !backboardd) return r;
    if (!surface) {r.reason = SURFACE062_NIL; return r;}
    if (!io || !io->read || !io->write || cache < SURFACE062_BASE ||
        cache - SURFACE062_BASE > UINT64_C(0x100000000) || context == surface ||
        !surface062_pointer(context, 0x600) || !surface062_pointer(surface, 0xc8)) {
        r.reason = SURFACE062_INVALID; return r;
    }
    if (surface062_read64(io, context, &r.vptr)) {r.reason = SURFACE062_READ_FAILED; return r;}
    if (r.vptr != cache + (SURFACE062_SW_VPTR - SURFACE062_BASE)) {
        r.reason = SURFACE062_OTHER_BACKEND; return r;
    }
    if (surface062_read64(io, r.vptr + 0x2e0, &r.import)) {r.reason = SURFACE062_READ_FAILED; return r;}
    if (r.import != cache + (SURFACE062_SW_IMPORT - SURFACE062_BASE)) {
        r.reason = SURFACE062_INVALID; return r;
    }
    uint64_t heads[2] = {0, 0};
    if (surface062_read64(io, context + 0x58, &heads[0]) ||
        surface062_read64(io, context + 0x60, &heads[1]) ||
        surface062_read32(io, surface, &r.references) ||
        surface062_read32(io, surface + 0x5c, &r.flags) ||
        surface062_read32(io, surface + 0x90, &r.state_flags) ||
        surface062_read64(io, surface + 0x10, &r.next) ||
        surface062_read64(io, surface + 0xb8, &r.owner)) {
        r.reason = SURFACE062_READ_FAILED; return r;
    }
    unsigned selected = (r.flags & 0x400) ? 1 : 0;
    r.head_address = context + (selected ? 0x60 : 0x58);
    r.head = heads[selected];
    for (unsigned i = 0; i < 2; ++i) {
        int found = surface062_find(io, heads[i], surface, &r.nodes);
        if (found < 0) {
            r.reason = found == -2 ? SURFACE062_SCAN_LIMIT_REACHED : SURFACE062_READ_FAILED; return r;
        }
        if (found) {
            r.reason = i == selected ? SURFACE062_ALREADY_TRACKED : SURFACE062_FOREIGN_LINK;
            return r;
        }
    }
    if (r.next) {r.reason = SURFACE062_FOREIGN_LINK; return r;}
    /* AsynchronousNode passes mode=1, offsets=0,0; SW's data constructor sets format=0xf,
     * one fresh reference, externally owned memory and a retained nonnull IOSurface at +0xb8. */
    uint32_t width = 0, height = 0, release_flags = 0;
    uint64_t stride = 0, memory = 0, bytes = 0;
    if (surface062_read32(io, surface + 0x28, &width) ||
        surface062_read32(io, surface + 0x2c, &height) ||
        surface062_read32(io, surface + 0x94, &release_flags) ||
        surface062_read64(io, surface + 0x98, &stride) ||
        surface062_read64(io, surface + 0xa0, &memory) ||
        surface062_read64(io, surface + 0xb0, &bytes)) {
        r.reason = SURFACE062_READ_FAILED; return r;
    }
    if (r.references != 1 || r.flags != 0xf ||
        (r.state_flags & UINT32_C(0xf0000001)) != UINT32_C(0x90000001) || !(release_flags & 1) ||
        !surface062_pointer(r.owner, 8) || !surface062_pointer(memory, 8) ||
        !width || !height || width > 16384 || height > 16384 || stride < (uint64_t)width * 4 ||
        stride > UINT64_MAX / height || bytes < stride * (height - 1) + (uint64_t)width * 4) {
        r.reason = SURFACE062_INVALID; return r;
    }
    uint64_t current = 0, current_other = 0, current_next = 0;
    uint32_t current_refs = 0, current_flags = 0;
    if (surface062_read64(io, r.head_address, &current) ||
        surface062_read64(io, context + (selected ? 0x58 : 0x60), &current_other) ||
        surface062_read64(io, surface + 0x10, &current_next) ||
        surface062_read32(io, surface, &current_refs) ||
        surface062_read32(io, surface + 0x5c, &current_flags)) {
        r.reason = SURFACE062_READ_FAILED; return r;
    }
    if (current != r.head || current_other != heads[1 - selected] || current_next != 0 ||
        current_refs != r.references || current_flags != r.flags) {
        r.reason = SURFACE062_STATE_CHANGED; return r;
    }
    r.reason = SURFACE062_PASS; return r;
    /* Original ordering: surface->tracked_next = old_head; context->head = surface. */
    if (io->write(io->opaque, surface + 0x10, &r.head, 8)) {
        r.reason = SURFACE062_WRITE_FAILED; return r;
    }
    if (io->write(io->opaque, r.head_address, &surface, 8)) {
        /* Do not undo a possibly committed head or overwrite concurrent user state. */
        if (surface062_read64(io, r.head_address, &current)) {
            r.reason = SURFACE062_COMMITTED_UNVERIFIED; return r;
        }
        if (current == surface) {
            r.committed = true; r.reason = SURFACE062_COMMITTED_UNVERIFIED; return r;
        }
        if (current != r.head) {r.reason = SURFACE062_STATE_CHANGED; return r;}
        uint64_t zero = 0;
        r.reason = io->write(io->opaque, surface + 0x10, &zero, 8) ?
            SURFACE062_ROLLBACK_FAILED : SURFACE062_WRITE_FAILED;
        return r;
    }
    r.committed = true;
    if (surface062_read64(io, r.head_address, &current) ||
        surface062_read64(io, surface + 0x10, &current_next) || current != surface || current_next != r.head) {
        r.reason = SURFACE062_COMMITTED_UNVERIFIED; return r;
    }
    r.verified = true; r.reason = SURFACE062_REPAIRED;
    return r;
}
