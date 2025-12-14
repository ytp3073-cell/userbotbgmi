from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Info Lookup</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
*{box-sizing:border-box;font-family:'Segoe UI',sans-serif}
body{
  margin:0;min-height:100vh;
  display:flex;align-items:center;justify-content:center;
  background:linear-gradient(-45deg,#0f2027,#203a43,#2c5364,#1c1c1c);
  background-size:400% 400%;
  animation:gradient 10s ease infinite;
  color:#fff;
}
@keyframes gradient{
  0%{background-position:0% 50%}
  50%{background-position:100% 50%}
  100%{background-position:0% 50%}
}
.card{
  width:92%;max-width:460px;
  padding:25px;
  border-radius:18px;
  background:rgba(255,255,255,0.12);
  backdrop-filter:blur(18px);
  box-shadow:0 0 40px rgba(0,0,0,.5);
}
h1{text-align:center;margin-bottom:18px;letter-spacing:1px}
.tabs{display:flex;margin-bottom:15px}
.tab{
  flex:1;padding:12px;
  cursor:pointer;
  border:1px solid rgba(255,255,255,.3);
  background:transparent;
  color:#fff;
  transition:.3s;
}
.tab.active{background:rgba(255,255,255,.25)}
.tab:hover{background:rgba(255,255,255,.2)}
.section{display:none}
.section.active{display:block}
input{
  width:100%;
  padding:12px;
  border-radius:10px;
  border:none;
  outline:none;
  margin-bottom:12px;
}
button{
  width:100%;
  padding:12px;
  border:none;
  border-radius:10px;
  background:linear-gradient(135deg,#00c6ff,#0072ff);
  color:#000;
  font-weight:bold;
  cursor:pointer;
  transition:.3s;
}
button:hover{
  transform:scale(1.03);
  box-shadow:0 0 15px #00c6ff;
}
pre{
  margin-top:15px;
  padding:12px;
  border-radius:10px;
  background:rgba(0,0,0,.5);
  max-height:260px;
  overflow:auto;
  white-space:pre-wrap;
  font-size:13px;
}
.footer{text-align:center;margin-top:10px;font-size:12px;opacity:.6}
</style>
</head>

<body>

<div class="card">
<h1>🔍 INFO LOOKUP</h1>

<div class="tabs">
  <div class="tab active" onclick="switchTab('mobile',this)">📱 Mobile</div>
  <div class="tab" onclick="switchTab('aadhaar',this)">🆔 Aadhaar</div>
</div>

<div id="mobile" class="section active">
  <input id="mobileInput" placeholder="Enter Mobile Number">
  <button onclick="checkMobile()">Check Mobile</button>
</div>

<div id="aadhaar" class="section">
  <input id="aadhaarInput" placeholder="Enter Aadhaar Number">
  <button onclick="checkAadhaar()">Check Aadhaar</button>
</div>

<pre id="output">Result will appear here...</pre>
<div class="footer">Powered by NEXTGEN</div>
</div>

<script>
function switchTab(id,el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  el.classList.add('active');
  document.getElementById(id).classList.add('active');
}

function show(data){
  output.textContent =
    typeof data === "object"
    ? JSON.stringify(data,null,2)
    : data;
}

function checkMobile(){
  let n = mobileInput.value.trim();
  if(!n) return show("Enter mobile number");
  show("Loading...");
  fetch("/api/mobile?number="+n)
    .then(r=>r.json())
    .then(show)
    .catch(()=>show("Error"));
}

function checkAadhaar(){
  let a = aadhaarInput.value.trim();
  if(!a) return show("Enter aadhaar number");
  show("Loading...");
  fetch("/api/aadhaar?aadhar="+a)
    .then(r=>r.json())
    .then(show)
    .catch(()=>show("Error"));
}
</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/api/mobile")
def mobile():
    number = request.args.get("number")
    if not number:
        return jsonify({"error": "number missing"})
    url = f"https://darkie.x10.mx/numapi.php?action=api&key=NEXTGEN&number={number}"
    return jsonify(requests.get(url, timeout=15).json())

@app.route("/api/aadhaar")
def aadhaar():
    a = request.args.get("aadhar")
    if not a:
        return jsonify({"error": "aadhar missing"})
    url = f"https://darkie.x10.mx/numapi.php?action=api&key=aa89dd725a6e5773ed4384fce8103d8a&aadhar={a}"
    return jsonify(requests.get(url, timeout=15).json())

# ✅ Vercel serverless handler
def handler(request, *args, **kwargs):
    return app(request, *args, **kwargs)
