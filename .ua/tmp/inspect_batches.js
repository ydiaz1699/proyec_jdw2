const fs = require('fs');
for (let i = 1; i <= 6; i++) {
  const res = JSON.parse(fs.readFileSync(`C:/Users/Alex/Desktop/1-Github/proyec_jdw2/.ua/tmp/ua-file-extract-results-${i}.json`, 'utf8'));
  console.log(`=== BATCH ${i} ===`);
  res.results.forEach(r => {
    const fnNames = (r.functions || []).map(f => f.name).slice(0, 5).join(', ');
    const clsNames = (r.classes || []).map(c => c.name).join(', ');
    console.log(`- ${r.path} (${r.fileCategory}, ${r.totalLines} lines): classes=[${clsNames}] funcs=[${fnNames}${r.functions && r.functions.length > 5 ? '... (' + r.functions.length + ')' : ''}]`);
  });
}
