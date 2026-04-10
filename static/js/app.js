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

/* --------------------------------------------------------------------------------------------------------------------- */

// History Page JavaScript

/**
 * Open modal with waste analysis details
 * @param {string} imagePath - Path to the scanned image
 * @param {string} prediction - AI prediction result
 * @param {string} confidence - Confidence percentage
 * @param {string} tip - Waste disposal tip
 * @param {string} date - Scan date
 */
function openModal(imagePath, prediction, confidence, tip, date) {
  const modal = document.getElementById('analysisModal');

  // Set modal content
  document.getElementById('modalImage').src = '/static/' + imagePath;
  document.getElementById('modalPrediction').textContent = prediction;
  document.getElementById('modalConfidence').textContent = confidence;
  document.getElementById('modalDate').textContent = date;
  document.getElementById('modalTip').textContent = tip;

  // Calculate RRR percentages based on prediction type
  let reduce, reuse, recycle;

  const predLower = prediction.toLowerCase();

  if (predLower.includes('non_recyclable') || predLower.includes('non-recyclable')) {
    // Non-recyclable: Focus on reducing waste
    reduce = 70;
    reuse = 20;
    recycle = 10;
    highlightCard('reduceCard');
  } else if (predLower.includes('recyclable')) {
    // Recyclable: Focus on recycling
    reduce = 20;
    reuse = 30;
    recycle = 50;
    highlightCard('recycleCard');
  } else if (predLower.includes('biodegradable')) {
    // Biodegradable: Focus on reusing/composting
    reduce = 30;
    reuse = 40;
    recycle = 30;
    highlightCard('reuseCard');
  } else {
    // Default equal distribution
    reduce = 33;
    reuse = 33;
    recycle = 34;
    highlightCard('recycleCard');
  }

  // Update percentage displays
  document.getElementById('reducePercent').textContent = reduce + '%';
  document.getElementById('reusePercent').textContent = reuse + '%';
  document.getElementById('recyclePercent').textContent = recycle + '%';

  // Show modal and prevent background scrolling
  modal.style.display = 'block';
  document.body.style.overflow = 'hidden';
}

/**
 * Highlight the dominant RRR card
 * @param {string} cardId - ID of the card to highlight
 */
function highlightCard(cardId) {
  // Remove active class from all cards
  document.querySelectorAll('.rrr-card').forEach(card => {
    card.classList.remove('active');
  });

  // Add active class to specified card
  const activeCard = document.getElementById(cardId);
  if (activeCard) {
    activeCard.classList.add('active');
  }
}

/**
 * Close the analysis modal
 */
function closeModal() {
  const modal = document.getElementById('analysisModal');
  modal.style.display = 'none';
  document.body.style.overflow = 'auto';
}

// Event listener for clicking outside modal to close
window.onclick = function(event) {
  const modal = document.getElementById('analysisModal');
  if (event.target === modal) {
    closeModal();
  }
};

// Keyboard support - ESC to close modal
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    closeModal();
  }
});

/* --------------------------------------------------------------------------------------------------------------------- */

// Dashboard/Index Page JavaScript

/**
 * Initialize dashboard functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  initializeImageUpload();
});

/**
 * Initialize image upload preview functionality
 */
function initializeImageUpload() {
  const imageInput = document.getElementById("imageInput");
  const previewBox = document.getElementById("previewBox");
  const previewImage = document.getElementById("previewImage");

  if (imageInput) {
    imageInput.addEventListener("change", function() {
      const file = this.files[0];
      if (file) {
        // Create object URL for preview
        const objectUrl = URL.createObjectURL(file);
        previewImage.src = objectUrl;
        previewBox.style.display = "block";

        // Clean up object URL when image loads to prevent memory leaks
        previewImage.onload = function() {
          URL.revokeObjectURL(objectUrl);
        };
      }
    });
  }
}

/**
 * Navigate to filtered history page
 * @param {string} filterType - 'reduce', 'reuse', or 'recycle'
 */
function navigateToFilteredHistory(filterType) {
  // Build URL with filter parameter
  const baseUrl = "/history";
  const url = filterType ? `${baseUrl}?filter=${filterType}` : baseUrl;
  window.location.href = url;
}

/**
 * Handle RRR button clicks with visual feedback
 * @param {HTMLElement} element - The clicked button element
 * @param {string} filterType - Filter type for navigation
 */
function handleRRRButtonClick(element, filterType) {
  // Add click animation
  element.style.transform = 'scale(0.95)';

  setTimeout(() => {
    element.style.transform = '';
    navigateToFilteredHistory(filterType);
  }, 150);
}

