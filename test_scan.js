const fs = require('fs');
const path = require('path');
const { promises: fsPromises } = fs;

async function run() {
    const sessionRoot = "C:/Users/jmj/.gemini/antigravity-ide";
    const brainDir = path.join(sessionRoot, "brain");
    const dirEntries = await fsPromises.readdir(brainDir, { withFileTypes: true }).catch(e => e);
    console.log("dirEntries length:", Array.isArray(dirEntries) ? dirEntries.length : dirEntries);
    
    const EXCLUDED_NAMES = new Set([".ds_store", "thumbs.db"]);
    async function collectFiles(dirPath, sessionRoot) {
        const files = [];
        const entries = await fsPromises.readdir(dirPath, { withFileTypes: true }).catch(e => ({error: e}));
        if (entries.error) return { ok: false, error: entries.error };
        
        for (const entry of entries) {
            if (EXCLUDED_NAMES.has(entry.name.toLowerCase()) || entry.name.endsWith("~")) continue;
            const fullPath = path.join(dirPath, entry.name);
            if (entry.isDirectory()) {
                const realPath = await fsPromises.realpath(fullPath).catch(e=>"ERR");
                const normReal = realPath.toLowerCase().replace(/\\/g, '/');
                const normRoot = sessionRoot.toLowerCase().replace(/\\/g, '/');
                if (!normReal.startsWith(normRoot)) {
                    console.log(`Symlink skip: ${fullPath} -> ${realPath}`);
                    continue;
                }
                const nested = await collectFiles(fullPath, sessionRoot);
                if (!nested.ok) return nested;
                files.push(...nested.files);
            } else if (entry.isFile()) {
                files.push(fullPath);
            }
        }
        return { ok: true, files };
    }
    
    for (const entry of Array.isArray(dirEntries) ? dirEntries : []) {
        if (!entry.isDirectory()) continue;
        const sessionId = entry.name;
        const sessionDir = path.join(brainDir, sessionId);
        console.log(`Checking sessionDir: ${sessionDir}`);
        const collected = await collectFiles(sessionDir, sessionRoot);
        console.log(`  collected files count: ${collected.files ? collected.files.length : "ERROR " + collected.error}`);
    }
}
run().catch(console.error);
