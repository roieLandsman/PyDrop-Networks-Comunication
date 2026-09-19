# Client Sync Folder Instructions

This folder is the default local folder watched by the PyDrop client.

## Responsibilities

- Hold files that should be synchronized with the server and other clients.
- Provide a simple location for demos.
- Allow the client to keep `.pydrop_state.json` as ignored local sync state.

## Rules

- Do not place source code here.
- Do not commit generated runtime files unless they are intentional small samples for documentation.
- Client code should avoid creating infinite sync loops when files in this folder were written because of server updates.
- Client code must not synchronize `.pydrop_state.json`.
