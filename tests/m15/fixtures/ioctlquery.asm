; SPDX-License-Identifier: GPL-2.0-or-later
; Historical IOCTL capability-query fields for internal CON and the local VA drive; FreeDOS behavior remains authoritative.
bits 16
cpu 8086
org 100h
%include "macros.inc"
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        ; CON has no Query IOCTL support flag, so DOS 5 specifies AX=1.
        mov bx, 1
        mov cx, 0345h
        mov ax, 4410h
        DOS 9050
        ERROR 1
%macro QUERY_BLOCK_IOCTL 2
        mov bx, 1
        mov cx, 0800h | %2
        mov ax, 4411h
        DOS %1
        SUCCESS
%endmacro
; DOS 5 requires capability success for each supported Function 440Dh minor.
QUERY_BLOCK_IOCTL 23100, 40h
QUERY_BLOCK_IOCTL 23101, 41h
QUERY_BLOCK_IOCTL 23102, 42h
QUERY_BLOCK_IOCTL 23103, 46h
QUERY_BLOCK_IOCTL 23104, 60h
QUERY_BLOCK_IOCTL 23105, 61h
QUERY_BLOCK_IOCTL 23106, 62h
QUERY_BLOCK_IOCTL 23107, 66h
; Sense Media Type and an unknown minor are unsupported by this drive.
        mov bx, 1
        mov cx, 0868h
        mov ax, 4411h
        DOS 23108
        ERROR 5
        mov bx, 1
        mov cx, 08ffh
        mov ax, 4411h
        DOS 23109
        ERROR 5
        jmp passed
result_name: db 'IOCTLQRY.RES',0
%include "harness.inc"
