# Client Sync Folder Instructions

This folder is the default local folder watched by the PyDrop client.

## Responsibilities

- Hold files that should be synchronized with the server and other clients.
- Provide a simple location for demos.

## Rules

- Do not place source code here.
- Do not commit generated runtime files unless they are intentional small samples for documentation.
- Client code should avoid creating infinite sync loops when files in this folder were written because of server updates.
