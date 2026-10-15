/**
 * CampusPulse DSU — Real-time AI Issue Reporting Assistant
 */

let typingTimer = null;
const DEBOUNCE_DELAY = 600;

document.addEventListener('DOMContentLoaded', () => {
    setupAIAnalysis();
    setupImagePreview();
});

function setupAIAnalysis() {
    const titleInput = document.getElementById('report-title');
    const descInput = document.getElementById('report-description');
    const spotInput = document.getElementById('report-spot');

    const inputs = [titleInput, descInput, spotInput];
    inputs.forEach(input => {
        if (!input) return;
        input.addEventListener('input', () => {
            clearTimeout(typingTimer);
            typingTimer = setTimeout(triggerAIAnalysis, DEBOUNCE_DELAY);
        });
    });
}

function triggerAIAnalysis() {
    const title = document.getElementById('report-title')?.value.trim() || '';
    const desc = document.getElementById('report-description')?.value.trim() || '';
    const spot = document.getElementById('report-spot')?.value.trim() || '';

    if (title.length < 5 && desc.length < 10) return;

    const aiCard = document.getElementById('ai-recommendation-card');
    const aiSpinner = document.getElementById('ai-analyzing-spinner');
    if (aiSpinner) aiSpinner.style.display = 'inline-block';

    fetch('/api/ai/analyze-issue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description: desc, specific_spot: spot })
    })
    .then(res => res.json())
    .then(data => {
        if (aiSpinner) aiSpinner.style.display = 'none';
        if (aiCard) aiCard.style.display = 'block';

        // Auto-select or suggest Category
        const catSelect = document.getElementById('report-category');
        const aiCatBadge = document.getElementById('ai-predicted-category');
        if (aiCatBadge) {
            aiCatBadge.textContent = data.predicted_category.toUpperCase();
            aiCatBadge.className = `badge badge-${data.predicted_category}`;
        }
        if (catSelect && (!catSelect.value || catSelect.dataset.userModified !== 'true')) {
            catSelect.value = data.predicted_category;
        }

        // Auto-select or suggest Priority
        const prioSelect = document.getElementById('report-priority');
        const aiPrioBadge = document.getElementById('ai-suggested-priority');
        if (aiPrioBadge) {
            aiPrioBadge.textContent = data.suggested_priority.toUpperCase();
            aiPrioBadge.className = `badge priority-${data.suggested_priority}`;
        }
        if (prioSelect && (!prioSelect.value || prioSelect.dataset.userModified !== 'true')) {
            prioSelect.value = data.suggested_priority;
        }

        // Confidence & Reasoning
        const confMeter = document.getElementById('ai-confidence-meter');
        const reasonText = document.getElementById('ai-reasoning-text');
        const impactText = document.getElementById('ai-impact-text');

        if (confMeter) confMeter.style.width = `${Math.round(data.confidence * 100)}%`;
        if (reasonText) reasonText.textContent = data.reasoning;
        if (impactText) impactText.textContent = data.estimated_impact;

        // Suggested Actions Checklist
        const actionList = document.getElementById('ai-actions-list');
        if (actionList && data.suggested_actions) {
            actionList.innerHTML = data.suggested_actions
                .map(act => `<li style="margin-bottom: 4px; font-size: 13px; color: #14532D;">✓ ${act}</li>`)
                .join('');
        }
    })
    .catch(err => {
        if (aiSpinner) aiSpinner.style.display = 'none';
        console.error("AI Analysis error:", err);
    });
}

function setupImagePreview() {
    const fileInput = document.getElementById('photo-input');
    const previewContainer = document.getElementById('photo-preview-container');
    const previewImg = document.getElementById('photo-preview-img');

    if (!fileInput || !previewContainer || !previewImg) return;

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                previewImg.src = event.target.result;
                previewContainer.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            previewContainer.style.display = 'none';
        }
    });
}
