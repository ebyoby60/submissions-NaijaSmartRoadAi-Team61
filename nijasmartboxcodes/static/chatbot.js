const container = document.getElementById("chatbox-container");
container.innerHTML = `
  <div id="chatbot">
    <div id="chat-header">AI Assistant</div>
    <div id="chat-messages"></div>
    <input id="chat-input" placeholder="Ask something..." />
  </div>
  <div id="chat-toggle"></div>
`;

document.getElementById("chat-toggle").onclick = () => {
  document.getElementById("chatbot").classList.toggle("open");
};

const input = document.getElementById("chat-input");
const messages = document.getElementById("chat-messages");

input.addEventListener("keypress", e => {
  if (e.key === "Enter" && input.value.trim()) {
    const msg = input.value.trim();
    addMsg("You", msg);
    input.value = "";
    respond(msg);
  }
});

function addMsg(sender, text) {
  messages.innerHTML += `<div><b>${sender}:</b> ${text}</div>`;
  messages.scrollTop = messages.scrollHeight;
}

function respond(msg) {
  let reply = "I'm here to assist with routes, traffic, or help info!";
  msg = msg.toLowerCase();
  if (msg.includes("route")) reply = "Check Dashboard for your route predictions.";
  else if (msg.includes("emergency")) reply = "Emergency vehicles get lowest congestion routes.";
  else if (msg.includes("help")) reply = "Visit Help page for more details.";
  else if (msg.includes("traffic")) reply = "AI predicts traffic congestion (Low, Medium, High).";
  setTimeout(() => addMsg("Bot", reply), 600);
}
