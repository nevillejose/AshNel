/**
 * ASHNEL INC. — Studio Website Client Logic
 */

// Step Navigation State
let currentStep = 1;

// Array of phrases for hero typewriter animation
const typewriterPhrases = [
  "Architected for Longevity,",
  "Battle-Tested Architecture,",
  "Built Lean for the AI Era,",
  "Delivered Without the Bloat,"
];

// Mobile Navigation Toggle & Initialization
document.addEventListener('DOMContentLoaded', () => {
  const mobileToggle = document.getElementById('mobile-menu-toggle');
  const mobileMenu = document.getElementById('mobile-menu');

  if (mobileToggle && mobileMenu) {
    mobileToggle.addEventListener('click', () => {
      mobileMenu.classList.toggle('hidden');
    });

    // Close menu when clicking links
    mobileMenu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mobileMenu.classList.add('hidden');
      });
    });
  }

  // Initialize Estimator Card Selection Classes
  setupRadioCardSelection();
  updateSummary();

  // Initialize Typewriter Animation
  initTypewriter();
});

// Typewriter Animation Logic
function initTypewriter() {
  const textEl = document.getElementById('typewriter-text');
  if (!textEl) return;

  let phraseIndex = 0;
  let charIndex = typewriterPhrases[0].length;
  let isDeleting = false;

  function tick() {
    const currentPhrase = typewriterPhrases[phraseIndex];

    if (isDeleting) {
      charIndex--;
      textEl.textContent = currentPhrase.substring(0, charIndex);
    } else {
      charIndex++;
      textEl.textContent = currentPhrase.substring(0, charIndex);
    }

    let nextDelay = isDeleting ? 35 : 65;

    if (!isDeleting && charIndex === currentPhrase.length) {
      // Hold for 3 seconds when fully typed
      nextDelay = 3000;
      isDeleting = true;
    } else if (isDeleting && charIndex === 0) {
      // Move to next phrase after erasing
      isDeleting = false;
      phraseIndex = (phraseIndex + 1) % typewriterPhrases.length;
      nextDelay = 400; // Brief pause before starting next word
    }

    setTimeout(tick, nextDelay);
  }

  // Hold the initial full text for 3 seconds before starting first erase cycle
  setTimeout(() => {
    isDeleting = true;
    tick();
  }, 3000);
}

// Setup visual highlights on radio card selection
function setupRadioCardSelection() {
  document.querySelectorAll('.track-option input[type="radio"]').forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.track-option').forEach(card => card.classList.remove('selected'));
      if (radio.checked) {
        radio.closest('.track-option').classList.add('selected');
      }
    });
    // Set initial
    if (radio.checked) {
      radio.closest('.track-option').classList.add('selected');
    }
  });

  document.querySelectorAll('.timeline-option input[type="radio"]').forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.timeline-option').forEach(card => card.classList.remove('selected'));
      if (radio.checked) {
        radio.closest('.timeline-option').classList.add('selected');
      }
    });
    // Set initial
    if (radio.checked) {
      radio.closest('.timeline-option').classList.add('selected');
    }
  });
}

// Navigation between estimator steps
function goToStep(step) {
  currentStep = step;

  // Hide all step contents
  document.getElementById('step-1-content').classList.add('hidden');
  document.getElementById('step-2-content').classList.add('hidden');
  document.getElementById('step-3-content').classList.add('hidden');

  // Show target step
  const activeContent = document.getElementById(`step-${step}-content`);
  if (activeContent) {
    activeContent.classList.remove('hidden');
  }

  // Update step indicator styles
  for (let i = 1; i <= 3; i++) {
    const indicator = document.getElementById(`step-indicator-${i}`);
    if (!indicator) continue;

    indicator.classList.remove('active', 'completed');
    if (i === step) {
      indicator.classList.add('active');
    } else if (i < step) {
      indicator.classList.add('completed');
    }
  }

  updateSummary();
}

// Update summary text in step 3
function updateSummary() {
  const trackInput = document.querySelector('input[name="project_track"]:checked');
  const timelineInput = document.querySelector('input[name="timeline"]:checked');

  const trackLabels = {
    'startup_mvp': 'New Startup MVP (Turnkey)',
    'faith_portal': 'Religious & Community Portal (Institutional Tech)',
    'compliance_setup': 'Regulatory, MSME & Compliance Tech'
  };

  const timelineLabels = {
    '30_days': '30-Day Velocity Sprint',
    '60_days': '60-Day Complete Platform',
    'exploratory': 'Exploratory Advisory & Blueprint'
  };

  const summaryTrack = document.getElementById('summary-track');
  const summaryTimeline = document.getElementById('summary-timeline');

  if (summaryTrack && trackInput) {
    summaryTrack.textContent = trackLabels[trackInput.value] || 'Startup MVP';
  }

  if (summaryTimeline && timelineInput) {
    summaryTimeline.textContent = timelineLabels[timelineInput.value] || '30-Day Sprint';
  }
}

// Handle Form Submission with Backend API Dispatch
async function handleFormSubmit() {
  const form = document.getElementById('intake-form');
  const successBox = document.getElementById('intake-success');
  const submitBtn = document.getElementById('intake-submit-btn');
  const submitText = document.getElementById('intake-submit-text');

  const trackInput = document.querySelector('input[name="track"]:checked');
  const timelineInput = document.querySelector('input[name="timeline"]:checked');
  const nameInput = document.getElementById('intake-name');
  const emailInput = document.getElementById('intake-email');
  const scopeInput = document.getElementById('intake-scope');
  const dpdpInput = document.getElementById('estimator-dpdp-consent');
  const hpInput = document.getElementById('intake-hp');

  const trackLabels = {
    'startup_mvp': 'New Startup MVP (Turnkey)',
    'faith_portal': 'Religious & Community Portal (Institutional Tech)',
    'compliance_setup': 'Regulatory, MSME & Compliance Tech'
  };

  const timelineLabels = {
    '30_days': '30-Day Velocity Sprint',
    '60_days': '60-Day Complete Platform',
    'exploratory': 'Exploratory Advisory & Blueprint'
  };

  const payload = {
    track: trackLabels[trackInput ? trackInput.value : ''] || 'Turnkey MVP',
    timeline: timelineLabels[timelineInput ? timelineInput.value : ''] || '30-Day Sprint',
    name: nameInput ? nameInput.value.trim() : '',
    email: emailInput ? emailInput.value.trim() : '',
    scope: scopeInput ? scopeInput.value.trim() : '',
    dpdp_consent: dpdpInput ? dpdpInput.checked : false,
    website_url_hp: hpInput ? hpInput.value.trim() : ''
  };

  if (submitBtn) submitBtn.disabled = true;
  if (submitText) submitText.textContent = 'Transmitting Brief to Studio...';

  try {
    const res = await fetch('/api/intake', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      if (form && successBox) {
        form.classList.add('hidden');
        successBox.classList.remove('hidden');
      }
    } else {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || 'Transmission error');
    }
  } catch (err) {
    console.error('Intake transmission error:', err);
    if (form && successBox) {
      form.classList.add('hidden');
      successBox.classList.remove('hidden');
      const fallbackNote = document.createElement('div');
      fallbackNote.className = 'mt-4 text-xs text-amber-800 bg-amber-50 p-3 rounded-xl border border-amber-200';
      fallbackNote.innerHTML = `Note: Direct dispatch link: <a href="mailto:ashnelinc.in@gmail.com?subject=Project%20Scope%20Brief%20(${encodeURIComponent(payload.name)})&body=${encodeURIComponent('Track: ' + payload.track + '\nTimeline: ' + payload.timeline + '\nScope: ' + payload.scope + '\nEmail: ' + payload.email)}" class="font-bold underline text-amber-900">Send via Email &rarr;</a>`;
      successBox.appendChild(fallbackNote);
    }
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    if (submitText) submitText.textContent = 'Submit & Open Advisory Calendar';
  }
}

// Reset Estimator
function resetIntake() {
  const form = document.getElementById('intake-form');
  const successBox = document.getElementById('intake-success');

  if (form && successBox) {
    form.reset();
    successBox.classList.add('hidden');
    form.classList.remove('hidden');
    setupRadioCardSelection();
    goToStep(1);
  }
}

// Modal Controllers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('hidden');
    // small timeout for transition
    setTimeout(() => {
      modal.classList.add('open');
    }, 10);
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
    setTimeout(() => {
      modal.classList.add('hidden');
    }, 200);
    document.body.style.overflow = '';
  }
}

// Close modal when clicking backdrop
window.addEventListener('click', (event) => {
  if (event.target.classList.contains('modal-backdrop')) {
    closeModal(event.target.id);
  }
});

// Close modal on Escape key
window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.open').forEach(modal => {
      closeModal(modal.id);
    });
  }
});

// Portfolio Category Filter Logic
function filterPortfolio(category) {
  // Update active filter button state
  document.querySelectorAll('.portfolio-filter-btn').forEach(btn => {
    if (btn.getAttribute('data-filter') === category) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Filter cards
  document.querySelectorAll('.portfolio-card').forEach(card => {
    const cardCategory = card.getAttribute('data-category');
    if (category === 'all' || cardCategory === category) {
      card.classList.remove('hidden-card');
    } else {
      card.classList.add('hidden-card');
    }
  });
}

