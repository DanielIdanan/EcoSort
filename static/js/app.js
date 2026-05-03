// ===================== SPLASH SCREEN =====================

window.addEventListener("load", () => {
  const splash = document.getElementById("splash-screen");
  const main = document.getElementById("main-content");

  if (splash && main) {
    setTimeout(() => {
      splash.classList.add("hide");
      main.classList.remove("hidden");
    }, 2500);
  }
});

// ===================== HISTORY PAGE =====================

/**
 * Open modal with waste analysis details
 * @param {string} imagePath  - Path to the scanned image
 * @param {string} prediction - AI prediction result
 * @param {string} confidence - Confidence percentage
 * @param {string} tip        - Waste disposal tip
 * @param {string} date       - Scan date
 * @param {string} probs      - Pipe-separated AI probabilities: "biodegradable|non_recyclable|recyclable"
 */
function openModal(imagePath, prediction, confidence, tip, date, probs) {
  const modal = document.getElementById("analysisModal");

  document.getElementById("modalImage").src = "/static/" + imagePath;
  document.getElementById("modalPrediction").textContent = prediction;
  document.getElementById("modalConfidence").textContent = confidence;
  document.getElementById("modalDate").textContent = date;
  document.getElementById("modalTip").textContent = tip;

  let reduce, reuse, recycle;

  // Try to use real AI probabilities first
  if (probs && probs !== "0|0|0" && probs.includes("|")) {
    const parts = probs.split("|").map(Number);
    // probs are stored as: biodegradable | non_recyclable | recyclable
    const bioProb  = parts[0] || 0;
    const nonProb  = parts[1] || 0;
    const recProb  = parts[2] || 0;

    // Map AI probabilities to RRR framework:
    // Reduce  ← non_recyclable probability (minimize waste that can't be processed)
    // Reuse   ← biodegradable probability  (compost / organic reuse)
    // Recycle ← recyclable probability     (send to recycling)
    const total = bioProb + nonProb + recProb || 100;
    reduce  = Math.round((nonProb / total) * 100);
    reuse   = Math.round((bioProb / total) * 100);
    recycle = 100 - reduce - reuse; // ensure they sum to 100
  } else {
    // Fallback to heuristics if probs not stored (old records)
    const predLower = prediction.toLowerCase();
    if (predLower.includes("non_recyclable") || predLower.includes("non-recyclable")) {
      reduce = 70; reuse = 20; recycle = 10;
    } else if (predLower.includes("recyclable")) {
      reduce = 10; reuse = 15; recycle = 75;
    } else if (predLower.includes("biodegradable")) {
      reduce = 15; reuse = 70; recycle = 15;
    } else {
      reduce = 33; reuse = 33; recycle = 34;
    }
  }

  // Highlight the dominant action card
  const predLower = prediction.toLowerCase();
  if (predLower.includes("non_recyclable") || predLower.includes("non-recyclable")) {
    highlightCard("reduceCard");
  } else if (predLower.includes("biodegradable")) {
    highlightCard("reuseCard");
  } else {
    highlightCard("recycleCard");
  }

  document.getElementById("reducePercent").textContent = reduce + "%";
  document.getElementById("reusePercent").textContent = reuse + "%";
  document.getElementById("recyclePercent").textContent = recycle + "%";

  modal.style.display = "block";
  document.body.style.overflow = "hidden";
}

/**
 * Highlight the dominant RRR card
 * @param {string} cardId - ID of the card to highlight
 */
function highlightCard(cardId) {
  document.querySelectorAll(".rrr-card").forEach(card => card.classList.remove("active"));
  const activeCard = document.getElementById(cardId);
  if (activeCard) activeCard.classList.add("active");
}

/**
 * Close the analysis modal
 */
function closeModal() {
  document.getElementById("analysisModal").style.display = "none";
  document.body.style.overflow = "auto";
}

// Close modal on backdrop click or ESC key
window.addEventListener("click", function (event) {
  if (event.target === document.getElementById("analysisModal")) closeModal();
});

document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") closeModal();
});

// ===================== DASHBOARD PAGE =====================

/**
 * Initialize image upload preview functionality
 */
function initializeImageUpload() {
  const imageInput = document.getElementById("imageInput");
  const previewBox = document.getElementById("previewBox");
  const previewImage = document.getElementById("previewImage");

  if (!imageInput) return;

  imageInput.addEventListener("change", function () {
    const file = this.files[0];
    if (file) {
      const objectUrl = URL.createObjectURL(file);
      previewImage.src = objectUrl;
      previewBox.style.display = "block";
      previewImage.onload = function () {
        URL.revokeObjectURL(objectUrl);
      };
    }
  });
}

document.addEventListener("DOMContentLoaded", initializeImageUpload);

/**
 * Navigate to filtered history page
 * @param {string} filterType - 'reduce', 'reuse', or 'recycle'
 */
function navigateToFilteredHistory(filterType) {
  const url = filterType ? `/history?filter=${filterType}` : "/history";
  window.location.href = url;
}

/**
 * Handle RRR button clicks with visual feedback
 * @param {HTMLElement} element    - The clicked button element
 * @param {string}      filterType - Filter type for navigation
 */
function handleRRRButtonClick(element, filterType) {
  element.style.transform = "scale(0.95)";
  setTimeout(() => {
    element.style.transform = "";
    navigateToFilteredHistory(filterType);
  }, 150);
}
