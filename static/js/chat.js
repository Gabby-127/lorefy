// Global state for current chat session
let currentChat = {
  sessionId: null,
  isComplete: false,
  turnCount: 0,
  maxTurns: 12,
  waitingForResponse: false,
  pendingIntervention: null,
};

function initChat() {
  const sessionIdElement = document.querySelector('[data-session-id]');
  if (sessionIdElement) {
    currentChat.sessionId = sessionIdElement.dataset.sessionId;
  }

  document.addEventListener("click", handleChatClick);
  document.addEventListener("keydown", handleKeyboardShortcuts);
}

function handleChatClick(e) {
  // Continue button
  if (e.target.classList.contains("chat-continue-btn")) {
    continueChat();
  }

  // Intervention options
  if (e.target.classList.contains("intervention-option")) {
    handleInterventionChoice(e.target);
  }

  // End screen buttons
  if (e.target.classList.contains("end-screen-action")) {
    const action = e.target.dataset.action;
    const characterId = e.target.dataset.characterId;
    if (action === "view-wiki") {
      window.location.href = `/character/${characterId}`;
    }
  }
}

function handleKeyboardShortcuts(e) {
  // Space bar to continue chat
  if (e.code === "Space" && !currentChat.isComplete && !currentChat.waitingForResponse) {
    const btn = document.querySelector(".chat-continue-btn");
    if (btn && !btn.disabled) {
      e.preventDefault();
      continueChat();
    }
  }
}

function continueChat() {
  if (currentChat.waitingForResponse || currentChat.isComplete) {
    return;
  }

  currentChat.waitingForResponse = true;
  const btn = document.querySelector(".chat-continue-btn");
  btn.disabled = true;
  btn.textContent = "...";

  const payload = {
    player_choice: currentChat.pendingIntervention || null,
  };

  fetch(`/chat/${currentChat.sessionId}/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        alert("Error: " + data.error);
        currentChat.waitingForResponse = false;
        btn.disabled = false;
        btn.textContent = "Continue →";
        return;
      }

      // Add messages to chat
      data.messages.forEach((msg) => {
        addMessageToChat(msg);
      });

      // Update character emotions and assets
      updateCharacterPanel("a", data.speaker_a_emotion, data.speaker_a_asset);
      updateCharacterPanel("b", data.speaker_b_emotion, data.speaker_b_asset);

      // Update turn counter
      currentChat.turnCount = data.turn_count;
      updateTurnCounter(data.turn_count);

      // Handle intervention
      currentChat.pendingIntervention = null;
      if (data.intervention && data.intervention.trigger) {
        showInterventionModal(data.intervention);
      }

      // Check if complete
      if (data.is_complete || data.turn_count >= 12) {
        endChat(data);
      } else {
        currentChat.waitingForResponse = false;
        btn.disabled = false;
        if (data.turn_count >= 12) {
          btn.textContent = "End Chat";
        } else {
          btn.textContent = "Continue →";
        }
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Failed to continue chat");
      currentChat.waitingForResponse = false;
      btn.disabled = false;
      btn.textContent = "Continue →";
    });
}

function addMessageToChat(msg) {
  const messagesContainer = document.querySelector(".chat-messages");
  if (!messagesContainer) return;

  const messageEl = document.createElement("div");
  messageEl.className = `chat-message from-${msg.speaker.toLowerCase()}`;

  const bubbleEl = document.createElement("div");
  bubbleEl.className = "chat-bubble";
  bubbleEl.textContent = msg.content;

  messageEl.appendChild(bubbleEl);
  messagesContainer.appendChild(messageEl);

  // Auto-scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function updateCharacterPanel(side, emotion, assetPath) {
  const panel = document.querySelector(`.chat-character-panel:${side === "a" ? "first-of-type" : "last-of-type"}`);
  if (!panel) return;

  const emotionLabel = panel.querySelector(".chat-character-emotion");
  if (emotionLabel) {
    emotionLabel.textContent = emotion.charAt(0).toUpperCase() + emotion.slice(1);
  }

  if (assetPath) {
    const imageContainer = panel.querySelector(".chat-character-image");
    if (imageContainer) {
      // Remove placeholder span if present
      const span = imageContainer.querySelector("span");
      if (span) span.remove();

      let img = imageContainer.querySelector("img");
      if (!img) {
        img = document.createElement("img");
        imageContainer.appendChild(img);
      }

      // Server returns relative paths like "static/uploads/…" — prepend slash
      const src = assetPath.startsWith("/") ? assetPath : "/" + assetPath;
      if (img.getAttribute("src") !== src) {
        img.style.opacity = "0";
        img.onload = () => { img.style.transition = "opacity 0.2s"; img.style.opacity = "1"; };
        img.src = src;
      }
      // Flip is handled by .flipped CSS class on the container — don't add inline transform
    }
  }
}

function updateTurnCounter(turnCount) {
  const counter = document.querySelector(".chat-turn-counter");
  if (counter) {
    counter.textContent = `Turn ${turnCount} / 12`;
  }
}

function showInterventionModal(intervention) {
  const overlay = document.createElement("div");
  overlay.className = "intervention-overlay";

  const modal = document.createElement("div");
  modal.className = "intervention-modal";

  const trigger = document.createElement("div");
  trigger.className = "intervention-trigger";
  trigger.textContent = intervention.trigger;
  modal.appendChild(trigger);

  const options = document.createElement("div");
  options.className = "intervention-options";

  const option1 = document.createElement("button");
  option1.className = "intervention-option";
  option1.textContent = intervention.option_1;
  option1.onclick = () => {
    currentChat.pendingIntervention = intervention.option_1;
    overlay.remove();
    continueChat();
  };
  options.appendChild(option1);

  const option2 = document.createElement("button");
  option2.className = "intervention-option";
  option2.textContent = intervention.option_2;
  option2.onclick = () => {
    currentChat.pendingIntervention = intervention.option_2;
    overlay.remove();
    continueChat();
  };
  options.appendChild(option2);

  modal.appendChild(options);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

function endChat(finalData) {
  currentChat.isComplete = true;

  fetch(`/chat/${currentChat.sessionId}/end`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
    .then((res) => res.json())
    .then((data) => {
      showEndScreen(data, finalData);
    })
    .catch((error) => {
      console.error("Error ending chat:", error);
      showEndScreen(
        {
          summary: "The interaction was memorable.",
          relationship_score: finalData.relationship_score,
          relationship_label: finalData.relationship_label,
        },
        finalData
      );
    });
}

function showEndScreen(summary, finalData) {
  const overlay = document.createElement("div");
  overlay.className = "end-screen-overlay";

  const screen = document.createElement("div");
  screen.className = "end-screen";

  const title = document.createElement("h2");
  title.textContent = "Chat Complete";
  screen.appendChild(title);

  const summaryText = document.createElement("p");
  summaryText.textContent = summary.summary || "A meaningful interaction occurred.";
  screen.appendChild(summaryText);

  const relationshipLabel = document.createElement("div");
  relationshipLabel.className = "end-relationship-label";
  relationshipLabel.textContent = summary.relationship_label || finalData.relationship_label;
  screen.appendChild(relationshipLabel);

  const barContainer = document.createElement("div");
  barContainer.className = "end-relationship-bar";

  const score = summary.relationship_score || finalData.relationship_score;
  const percentage = (score / 10) * 100;
  const hue = (score - 1) * (120 / 9); // Red (0°) to Green (120°)

  const barFill = document.createElement("div");
  barFill.className = "end-relationship-bar-fill";
  barFill.style.width = percentage + "%";
  barFill.style.background = `hsl(${hue}, 100%, 50%)`;
  barContainer.appendChild(barFill);
  screen.appendChild(barContainer);

  const actions = document.createElement("div");
  actions.className = "end-screen-actions";

  // Get character IDs from DOM
  const charAPanel = document.querySelector(".chat-character-panel:first-of-type");
  const charBPanel = document.querySelector(".chat-character-panel:last-of-type");
  const charAId = charAPanel ? charAPanel.dataset.characterId : null;
  const charBId = charBPanel ? charBPanel.dataset.characterId : null;

  if (charAId) {
    const btn1 = document.createElement("button");
    btn1.className = "end-screen-action";
    btn1.dataset.action = "view-wiki";
    btn1.dataset.characterId = charAId;
    btn1.textContent = `View Character A's Wiki`;
    actions.appendChild(btn1);
  }

  if (charBId) {
    const btn2 = document.createElement("button");
    btn2.className = "end-screen-action";
    btn2.dataset.action = "view-wiki";
    btn2.dataset.characterId = charBId;
    btn2.textContent = `View Character B's Wiki`;
    actions.appendChild(btn2);
  }

  screen.appendChild(actions);
  overlay.appendChild(screen);
  document.body.appendChild(overlay);
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initChat);
} else {
  initChat();
}