# M13 integration inventory (source-backed)

The M12 PC-88VA carrier links `startup`, `loader_services`, `console`,
`machine_services`, `console_input`, `resident_disk`, and the small
`platform.lib` containing only the fail-closed platform probe and NLS stub.
The common FreeDOS DOS core objects, block request/DPB layer, FAT/file
handles, memory allocator/PSP, EXEC path, and console device strategy are not
linked by this target and remain unverified here.

M13 must establish the request-packet and DPB boundary around the M12
resident read ABI, then add filesystem handles and process/memory ownership in
separate bounded steps. It must not infer these interfaces from the
`KERNEL.SYS` filename or from FreeCOM payload presence.
