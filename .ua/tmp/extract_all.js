const fs = require('fs');
const { execSync } = require('child_process');

const batchesPath = 'C:/Users/Alex/Desktop/1-Github/proyec_jdw2/.ua/intermediate/batches.json';
const batches = JSON.parse(fs.readFileSync(batchesPath, 'utf8'));

for (let i = 1; i <= batches.batches.length; i++) {
  const b = batches.batches[i - 1];
  const input = {
    projectRoot: 'C:/Users/Alex/Desktop/1-Github/proyec_jdw2',
    batchFiles: b.files,
    batchImportData: b.batchImportData || {}
  };
  const inputFile = `C:/Users/Alex/Desktop/1-Github/proyec_jdw2/.ua/tmp/ua-file-analyzer-input-${i}.json`;
  const outputFile = `C:/Users/Alex/Desktop/1-Github/proyec_jdw2/.ua/tmp/ua-file-extract-results-${i}.json`;
  fs.writeFileSync(inputFile, JSON.stringify(input, null, 2));
  console.log(`Extracting batch ${i}...`);
  execSync(`node "C:/SKILL_config/Understand-Anything/understand-anything-plugin/skills/understand/extract-structure.mjs" "${inputFile}" "${outputFile}"`, { stdio: 'inherit' });
}
console.log('All extractions complete!');
