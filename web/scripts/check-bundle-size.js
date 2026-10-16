import fs from 'fs';
import path from 'path';
import zlib from 'zlib';

const distDir = path.resolve('dist', 'assets');
const MAX_GZIP_BYTES = 300 * 1024; // 300 KB budget per SC-010

if (!fs.existsSync(distDir)) {
  console.error(`Dist directory ${distDir} not found. Run vite build first.`);
  process.exit(1);
}

let totalGzipBytes = 0;
const files = fs.readdirSync(distDir);

console.log('--- Client Bundle Size Audit (Budget: <300 KB gzipped) ---');
for (const file of files) {
  if (file.endsWith('.js')) {
    const fullPath = path.join(distDir, file);
    const content = fs.readFileSync(fullPath);
    const gzipped = zlib.gzipSync(content);
    totalGzipBytes += gzipped.length;
    console.log(`  ${file}: ${(gzipped.length / 1024).toFixed(2)} KB (gzipped)`);
  }
}

const totalKb = (totalGzipBytes / 1024).toFixed(2);
console.log(`Total JS Bundle: ${totalKb} KB / 300.00 KB`);

if (totalGzipBytes > MAX_GZIP_BYTES) {
  console.error(`[FAIL] Bundle budget exceeded: ${totalKb} KB > 300 KB`);
  process.exit(1);
} else {
  console.log(`[PASS] Bundle budget satisfied: ${totalKb} KB < 300 KB`);
}
