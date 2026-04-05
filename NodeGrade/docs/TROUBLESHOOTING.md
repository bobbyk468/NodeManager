# Troubleshooting

## Vite error: `ENOENT ... stat '.../.pnp.cjs'`

This repo uses **`nodeLinker: node-modules`** (see `.yarnrc.yml`), so there is **no** `.pnp.cjs` file. If your shell still has a leftover Yarn PnP hook, Node tries to load a missing file.

**Fix (pick one):**

1. **One-off in the terminal** before `yarn dev`:
   ```bash
   unset NODE_OPTIONS
   ```
   (PowerShell: `Remove-Item Env:NODE_OPTIONS -ErrorAction SilentlyContinue`)

2. **Permanent:** Remove any line in `~/.zshrc`, `~/.bashrc`, or IDE/Cursor settings that sets:
   ```bash
   export NODE_OPTIONS="--require .../.pnp.cjs"
   ```

3. The frontend `dev` script clears `NODE_OPTIONS` for the Vite process (`env -u NODE_OPTIONS`). If you still see the error, run step 1 in the same terminal.

Then reinstall and start again:

```bash
cd NodeManager/NodeGrade
corepack yarn install
corepack yarn workspace @haski/ta-frontend dev
```
