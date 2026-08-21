---
description: Debug a live Nexlayer deployment — namespace info, logs, exec, file edits, DB queries, restarts.
argument-hint: "[application name or symptom]"
---

Invoke the `debug-nexlayer` skill for $ARGUMENTS.

You need the `applicationName` from the user's `nexlayer.yaml` before deploying the debug proxy — ask for it if it was not given. Deploy the proxy once, start with `nexlayer_debug_namespace_info`, and only call the tools the symptom calls for.
