; SPDX-License-Identifier: GPL-2.0-or-later
; Read the complete DOS arena from the documented list-of-lists MCB pointer.
; No fixed physical address or assumed conventional-memory end is used.
walk_arena:
        mov bx, [arena_first]
        mov cx, 256
        mov word [own_blocks], 0
.next:
        mov es, bx
        mov al, [es:0]
        cmp al, 'M'
        je .type_ok
        cmp al, 'Z'
        jne arena_failure
.type_ok:
        mov di, [chain_next]
        cmp di, chain_limit-10
        ja arena_failure
        mov dx, [case_id]
        mov [di], dx
        mov [di+2], bx
        xor ah, ah
        mov [di+4], ax
        mov dx, [es:1]
        mov [di+6], dx
        cmp dx, [psp]
        jne .other_owner
        inc word [own_blocks]
.other_owner:
        mov dx, [es:3]
        mov [di+8], dx
        add di, 10
        mov [chain_next], di
        inc word [chain_count]
        add dx, bx
        jc arena_failure
        inc dx
        jz arena_failure
        cmp dx, bx
        jbe arena_failure
        cmp al, 'Z'
        je .last
        mov bx, dx
        loop .next
        jmp arena_failure
.last:
        cmp word [arena_end], 0
        je .initial
        cmp dx, [arena_end]
        jne arena_failure
.initial:
        mov [arena_end], dx
        push cs
        pop es
        ret
arena_failure:
        push cs
        pop ds
        push cs
        pop es
        jmp failure
save_chain:
        push cs
        pop ds
        push cs
        pop es
        mov dx, chain_name
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc report_failure
        mov [chain_handle], ax
        mov bx, ax
        mov dx, chain_report
        mov cx, [chain_next]
        sub cx, chain_report
        mov [chain_length], cx
        mov ah, 40h
        int 21h
        jc report_failure
        cmp ax, [chain_length]
        jne report_failure
        mov bx, [chain_handle]
        mov ah, 3eh
        int 21h
        jc report_failure
        ret
arena_first: dw 0
arena_end: dw 0
psp: dw 0
own_blocks: dw 0
base_owned: dw 0
chain_handle: dw 0
chain_length: dw 0
chain_next: dw chain_records
%ifndef M15_CHAIN_NAME
%define M15_CHAIN_NAME 'MEMORY.MCB'
%endif
chain_name: db M15_CHAIN_NAME,0
chain_report: db 'M15M'
        dw 1
chain_count: dw 0
chain_records: times 2048*10 db 0
chain_limit:
