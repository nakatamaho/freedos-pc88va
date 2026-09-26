# M15 local FreeDOS service profile

Status: **DRAFT; inventory and qualification remain in progress.**

M15 ports the actual M14 common FreeDOS kernel and packaged FreeCOM to PC-88VA,
running on the VA adapter with FAT12 media, ASCII/8.3 names and the qualified
native 512-KiB configuration.
The build uses Open Watcom 1.9, 8086 instructions, medium-model code and near
data, with `PC88VA` and `M13WATCOM` selected. FAT32, optional LFN, DEBUG and
TSC build guards are absent. The inherited FreeCOM build is the generic ASCII,
English, no-XMS-swap configuration used by M14 through the VA DOS console; it
is not a separately defined NECPC88VA compiler option. This target makes no
claim of IBM/NEC98 BIOS or general MS-DOS compatibility. Microsoft references
are guidance; do not change upstream FreeDOS behavior solely to match them or
to repair an existing upstream FreeDOS bug. Fix VA-specific port defects.

The kernel may report its actual FreeDOS version as 5.2. M15 does not rewrite
that value or claim an MS-DOS compatibility level from it.

The [machine-readable inventory](../../config/m15/api-inventory.json) records
the active dispatch surface, unavailable services, later DOS additions, and
undocumented entries. Its 221 rows are dispatch-entry QA keys, not 221
independent behavior contracts. The locked source boundary is
[`m15-api-boundary.md`](m15-api-boundary.md): 221 unique dispatch-entry IDs in
total, comprising 113 `REQUIRED` FreeDOS services, 82 `OUT_OF_PROFILE` entries,
and 26 `UNDOCUMENTED_OBSERVATION` entries. The finite set is derived from the
pinned kernel dispatch/build guards, selected FreeCOM callers, and accepted
M15 feature profile. Six MS-DOS reference questions are deferred under issues
#3-#6; their API rows and recorded ordinary observations remain in scope. The
221 total is a count of the local locked inventory, not a number published by
a DOS manual. Each ID is one test-boundary unit; input, packet, error and state
variants remain cases within that ID. Adding an entry requires a reviewed,
source-backed versioned scope amendment.

Microsoft's *MS-DOS Encyclopedia* and other published references help identify
common DOS APIs and historical version conditions. They are not an expected-
behavior oracle for this port. The pinned FreeDOS source defines the DOS
behavior being ported; preserve it, including existing FreeDOS bugs or
differences from Microsoft DOS. Fix only VA-specific adapter, ABI, memory, and
integration defects. The locked inventory represents the selected active
services and excluded M15 features; it does not claim to implement a particular
Microsoft DOS release. Current FreeDOS dispatch and `docs/intfns.txt` establish
reachability and discovery.

The `CX=FFFFh` packet forms of INT 25h and INT 26h are retained as observations
outside the selected M15 feature profile. The MS-DOS 3.3 and 4.0 references
describe historical interfaces, not required behavior for the FreeDOS port.

The legacy sector-count forms remain active FreeDOS services. Their failure
register comparison is deferred under
[issue #5](https://github.com/nakatamaho/freedos-pc88va/issues/5); M15 does not
change FreeDOS solely to match one conflicting Microsoft reference.

UMB is outside this PC-88VA M15 memory profile.
`INT 21h/AH=58h, AL=02h/03h` remains inventoried but is out of profile; the
required allocation-strategy calls are only `AL=00h/01h`.

## Specification, implementation and observations

The selected upstream FreeDOS kernel and FreeCOM define the implementation
being ported. Published references help explain common interfaces but do not
impose exact MS-DOS compatibility. Test ordinary supported workflows and
VA-specific changes; preserve unrelated upstream behavior even when it differs
from an MS-DOS reference. The pinned kernel's `docs/intfns.txt` is a discovery
list, not runtime evidence.

The Microsoft *MS-DOS Programmer's Reference* (1991), functions 26h, 50h,
4B01h, 4B03h, 59h, 5Ah and 6Ch, provides context for load/overlay, PSP, error
and extended-file interfaces. A documented difference is not by itself a
reason to change the kernel's existing FreeDOS behavior.

EXEC termination restores the documented parent PSP, stack and termination,
break and critical-error vectors. It does not promise automatic restoration
of an arbitrary parent DTA. Fixtures explicitly reestablish their DTA before
using it after a child. Load-only fixtures release cloned handle references
and the new environment/program blocks under the appropriate current PSP.
Overlay storage remains caller-owned and its relocation factor is checked.

Original fixtures are GPL-2.0-or-later, 8086 assembly. The existing kernel
absolute-read test and FreeCOM batch tests remain candidate references; no
adapted upstream test is claimed as executed before its target assumptions
and actual invocation are recorded. Raw documentation copies stay outside Git.

Each inventory row keeps applicability separate from execution outcome. Its
`port_review_status` describes review and qualification progress; it does not
assert exact Microsoft behavior:

- `REQUIRED`: the supported local service requires meaningful runtime evidence.
- `OUT_OF_PROFILE`: the excluded capability does not count as supported; an
  available, defined rejection test is recorded separately.
- `UNDOCUMENTED_OBSERVATION`: preserve the observed legacy behavior without
  claiming a historical compatibility contract that has not been established.
- `DEFERRED_M15_PLUS`: an explicitly deferred MS-DOS reference question with a
  linked issue; it does not reclassify or invalidate the active FreeDOS API row.

`PASS`, `FAIL`, `NOT_RUN` and `BLOCKED` are outcomes, not applicability choices.
A failed mandatory service cannot become an exclusion. Network/SHARE,
physical AUX/PRN, new HMA/UMB/EMS/XMS facilities, FAT16/FAT32, LFN and Japanese
I/O remain outside M15. Existing local machine-name state, ASCII country
conversion, switch-character state and other active local services remain
in the inventory even when their original use was a broader environment.

DOS 3.3 internationalization calls, including INT 21h/AH=65h/66h and the
associated NLS multiplex interface, are outside the selected M15 ASCII profile.
Separately, the existing M15 build has no NLSFUNC provider and does not enable
global code-page switching. Candidate results for those calls remain observations or
out-of-profile checks; they do not count as supported-feature coverage.

## Original recorder and assertions

`invoke21` captures actual AX/BX/CX/DX/SI/DI/BP/DS/ES, FLAGS and the stack
difference immediately after INT 21h. It then restores the fixture's DS/ES;
returned segment values remain in the record. No output flags or values are
patched. Only defined outputs are assertions. Each case records its stable ID
before calling DOS, and retains its unchecked result in memory before file
reporting. Overflow, a missing case, duplicate/order drift, an unchecked
assertion, a nonzero failure ID or a stack imbalance prevents acceptance.

FCBs use AL status, with CX record counts for block calls. They do not inherit
the handle API's CF/error convention. Handle and pathname calls check their
documented CF/AX contract. FindFirst permits the documented file-not-found or
no-match error for an absent match; FindNext exhaustion requires no-more-files.
The original overly narrow FindFirst assertion is corrected from this primary
contract, with the failed diagnostic retained locally. No kernel repair follows
from that diagnostic.

The saved result is independently decoded, and all FAT copies, chains, files
and sentinel payloads are checked on the host. Fresh-boot rereads are separate
required evidence. A fixture's completion text, an emulator exit or an empty
result is insufficient. Build pairs come from isolated deterministic exports
inside the pinned Linux/amd64 environment. ROMs, media, observations and concrete
runtime bindings remain in persistent excluded storage.

Final acceptance still requires every mandatory family, practical writable
FreeCOM, guest system transfer and independent target boot, resource lifetime,
persistence, historical regression, exact-head CI and exact-image handoff.
Automated frontend input is separate from manual operation. Hardware is NOT RUN.

The accepted M14 media-lifetime policy also applies during M15 console and
idle sessions: changed or unknown media invalidates existing file handles.
An unchanged physical image alone does not establish a continuously valid
binding. Commit and close completed writes before extended idle periods;
after an invalidation, close the stale reference and open the pathname again.
Uncommitted data can be lost under the existing contract. Break-handler
recovery and unknown-media rejection are checked separately, without adding
native status queries that could alter the condition being observed.
