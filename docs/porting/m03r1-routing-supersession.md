# M03R1 Routing Supersession Record

M03 commit `1d885d24ab1aaf5e23b9b5e00b376c5a93165f31` recorded a complete
tracked-source census and accepted independent-platform ADR. Its canonical
census used one scalar `target_milestone`, incorrectly treating each regex or
static-analysis observation as an exclusive implementation owner.

M03R1 supersedes only that routing schema and its membership counts. It
retains the 14,455 source observations, source matching, ADR decision,
private-source boundary, and twelve-item M04 blocker ledger. The old 10 MB
golden remains in Git history and is not duplicated for archival convenience.

| identity | superseded M03 | M03R1 replacement |
| --- | --- | --- |
| golden size | 10,530,917 bytes | 14,637,790 bytes |
| golden SHA-256 | `d075493a14b5913f968d30c284e625fc5e38f37300505fa557d948eabdc99f45` | `d871c7f188313218c2c9481ea9fe7c6abf6acd6369f996b2641021ad27c80550` |
| scanner/ruleset SHA-256 | `6d362672a193896e68531d2701f2645006d294d146cda408727981cefddddc52` | `57b8b299537bb9ca226e48cbd5bbf5dfe19da87d89ca3250c56a008fb9b0934c` |
| entry count | 14,455 | 14,455 |

The accepted routing-free projection is schema version 1, 10,039,882 bytes,
and SHA-256
`70bee9fedaa526f58a795c2acd43e3492a23e1554bcf843160bce7316120a42c`
before and after M03R1. Byte identity of that projection, not replacement of
the golden alone, proves that the source observation set did not change.

The replacement schema SHA-256 is
`08af162ec4c6def748ebc57e1b48aa7e38a82e203615feb736458b53c8b35548`.
The routing-policy SHA-256 is
`dbb28f45c16d59b97fab8defa21ce4a866d51c701826987ce26a3b50ad8c938e`.

No M01R1 or M02R1 evidence is superseded. M04 remains specification-only and
has not started; M06 remains the first milestone permitted to add PC-88VA
porting code.
