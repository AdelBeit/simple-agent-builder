const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const CSV = path.join(__dirname, 'submissions.csv');

app.use(express.json());
app.use(express.static(__dirname));

if (!fs.existsSync(CSV)) {
  fs.writeFileSync(CSV, 'name,phone,email,service,message,date\n');
}

app.post('/contact', (req, res) => {
  const { name, phone = '', email = '', service = '', message = '' } = req.body;
  const date = new Date().toISOString();
  const row = [name, phone, email, service, message, date]
    .map(v => `"${String(v).replace(/"/g, '""')}"`)
    .join(',');
  fs.appendFileSync(CSV, row + '\n');
  console.log(`[LEAD] ${date} — ${name} | ${phone} | ${service}`);
  res.json({ ok: true });
});

app.listen(3100, () => console.log('Peak Flow Plumbing → http://localhost:3100'));
