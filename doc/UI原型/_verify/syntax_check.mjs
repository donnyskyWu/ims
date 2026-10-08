import fs from 'fs';
const html = fs.readFileSync('UI原型/IMS-完整系统-UI原型.html', 'utf8');
const re = /<script>([\s\S]*?)<\/script>/g;
let m, i = 0, errors = 0;
const blocks = [];
while ((m = re.exec(html)) !== null) { blocks.push({ idx: i++, start: m.index, code: m[1] }); }
console.log('script blocks:', blocks.length);
blocks.forEach((b, k) => {
  const lineNo = html.slice(0, b.start).split('\n').length;
  try { new Function(b.code); console.log(`  block#${k} (starts ~line ${lineNo}, ${b.code.length} chars): OK`); }
  catch (e) { errors++; console.log(`  block#${k} (starts ~line ${lineNo}): SYNTAX ERROR -> ${e.message}`); }
});
console.log(errors === 0 ? 'ALL_SYNTAX_OK' : 'SYNTAX_ERRORS=' + errors);