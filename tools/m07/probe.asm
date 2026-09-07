; SPDX-License-Identifier: GPL-2.0-or-later
; Deterministic compile-only firmware handoff marker for M07.

bits 16
org 62

probe_entry:
    xchg ax, ax
    xchg bx, bx
    xchg cx, cx
    xchg dx, dx

probe_stop:
    jmp probe_stop
