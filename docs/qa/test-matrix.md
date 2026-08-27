# QA Test Matrix

| Layer | Scope | M00 status |
| --- | --- | --- |
| Host | Static, reproducibility, and scaffold checks | HOST PASS when the listed checks pass |
| VAEG local | May use local ROM/OS/private fixtures; outside public CI | NOT RUN |
| VAEG BIOS | BIOS-only payload testing | NOT RUN |
| VAEG romless | Future public I/O-level testing | NOT RUN |
| Hardware | Optional manual PC-88VA evidence; non-blocking | NOT RUN |

`HARDWARE PASS` requires an actual hardware result. No VAEG or hardware result
is implied by host scaffold validation.
