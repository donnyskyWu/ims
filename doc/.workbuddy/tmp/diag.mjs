import fs from 'fs';
import vm from 'vm';
const html = fs.readFileSync('UI原型/IMS-完整系统-UI原型.html', 'utf8');
const re = /<script>([\s\S]*?)<\/script>/g;
let m, i = 0;
while ((m = re.exec(html)) !== null) {
  if (i === 2) {
    const startLine = html.slice(0, m.index).split('\n').length;
    try { new vm.Script(m[1], { filename: 'block2.js' }); console.log('OK'); }
    catch (e) {
      console.log('block starts at file line', startLine);
      console.log(e.stack);
      const lines = m[1].split('\n');
      const mm = /block2\.js:(\d+)/.exec(e.stack);
      if (mm) {
        const ln = parseInt(mm[1], 10);
        console.log('--- around block line ' + ln + ' (file line ' + (startLine + ln) + ') ---');
        for (let k = Math.max(0, ln - 4); k < Math.min(lines.length, ln + 3); k++) {
          console.log((startLine + k + 1) + ': ' + lines[k]);
        }
      }
    }
  }
  i++;
}
