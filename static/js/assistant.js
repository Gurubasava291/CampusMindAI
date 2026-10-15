/**
 * CampusPulse DSU — DSU EcoBot Interactive Sustainability Assistant Client
 * Enhanced with real-time text problem diagnosis and 1-click in-chat ticket creation.
 */

let campusLocations = [];

document.addEventListener('DOMContentLoaded', () => {
    // Load embedded locations
    const locScript = document.getElementById('locations-data');
    if (locScript) {
        try {
            campusLocations = JSON.parse(locScript.textContent);
        } catch (e) {
            console.error("Error parsing campus locations:", e);
        }
    }

    const chatForm = document.getElementById('assistant-chat-form');
    const chatInput = document.getElementById('assistant-input');
    const imageInput = document.getElementById('assistant-image-input');
    const imageName = document.getElementById('assistant-image-name');
    const messagesBox = document.getElementById('chat-messages-box');
    const suggestionsBox = document.getElementById('chat-suggestions-box');

    if (!chatForm || !chatInput || !messagesBox) return;

    if (imageInput && imageName) {
        imageInput.addEventListener('change', () => {
            imageName.textContent = imageInput.files[0]?.name || 'Attach image';
        });
    }

    // Handle problem presets click
    document.querySelectorAll('.problem-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const problemText = btn.getAttribute('data-text');
            if (problemText) {
                chatInput.value = problemText;
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    });

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        const imageFile = imageInput?.files[0];
        if (!text && !imageFile) return;

        appendMessage('user', text || 'Please analyze this image.', null, null, imageFile);
        chatInput.value = '';
        if (imageInput) imageInput.value = '';
        if (imageName) imageName.textContent = 'Attach image';

        // Show typing indicator
        const typingId = appendTypingIndicator();

        const requestOptions = imageFile
            ? {
                method: 'POST',
                body: (() => {
                    const formData = new FormData();
                    formData.append('image', imageFile);
                    formData.append('prompt', text);
                    return formData;
                })()
            }
            : {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            };
        const endpoint = imageFile ? '/api/assistant/analyze-image' : '/api/assistant/chat';

        fetch(endpoint, requestOptions)
        .then(async res => {
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(data.error || 'The request could not be completed.');
            return data;
        })
        .then(data => {
            removeTypingIndicator(typingId);
            appendMessage('bot', data.reply, data.diagnosis, data.actions);

            // Update suggestions if any
            if (suggestionsBox && data.suggestions) {
                renderSuggestions(data.suggestions);
            }
        })
        .catch(err => {
            removeTypingIndicator(typingId);
            appendMessage('bot', err.message || "Sorry, I encountered a temporary connection issue. Please try again.");
            console.error(err);
        });
    });

    // Delegated handler for all interactive action buttons (links + prompt chips)
    messagesBox.addEventListener('click', (e) => {
        const btn = e.target.closest('.action-btn');
        if (!btn) return;

        const link = btn.getAttribute('data-action-link');
        if (link) {
            window.location.href = link;
            return;
        }
        const prompt = btn.getAttribute('data-action-prompt');
        if (prompt) {
            chatInput.value = prompt;
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Handle suggestion pills click
    if (suggestionsBox) {
        suggestionsBox.addEventListener('click', (e) => {
            const pill = e.target.closest('.suggestion-pill');
            if (pill) {
                const query = pill.textContent.trim();
                chatInput.value = query;
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    function appendMessage(sender, text, diagnosis = null, actions = null, imageFile = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${sender}-message`;

        const isBot = sender === 'bot';
        const avatar = isBot ? '🤖' : '👤';

        // Escape raw HTML first (bot output is trusted markdown, user input is escaped)
        const safeText = escapeHtml(text);

        // Markdown formatting
        const formattedText = safeText
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background: rgba(0,0,0,0.06); padding: 2px 6px; border-radius: 4px; font-weight: 600;">$1</code>')
            .replace(/\n/g, '<br>');

        let diagnosisCardHtml = '';
        if (diagnosis) {
            diagnosisCardHtml = createDiagnosisCard(diagnosis);
        }

        let actionsHtml = '';
        if (actions && actions.length) {
            actionsHtml = createActionsHtml(actions);
        }

        msgDiv.innerHTML = `
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-bubble" style="${diagnosis ? 'max-width: 100%; border: 1.5px solid #86EFAC;' : ''}">
                ${formattedText}
                ${actionsHtml}
                ${diagnosisCardHtml}
            </div>
        `;

        if (imageFile) {
            const imagePreview = document.createElement('img');
            const imageUrl = URL.createObjectURL(imageFile);
            imagePreview.className = 'chat-image-attachment';
            imagePreview.src = imageUrl;
            imagePreview.alt = 'Image sent for analysis';
            imagePreview.addEventListener('load', () => URL.revokeObjectURL(imageUrl), { once: true });
            msgDiv.querySelector('.msg-bubble').append(imagePreview);
        }

        messagesBox.appendChild(msgDiv);
        messagesBox.scrollTop = messagesBox.scrollHeight;

        // If card was attached, attach its submit handler
        if (diagnosis) {
            setupQuickTicketHandler(msgDiv, diagnosis);
        }
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function createActionsHtml(actions) {
        const buttons = actions.map(a => {
            const label = escapeHtml(a.label || '');
            if (a.type === 'link' && a.url) {
                return `<button type="button" class="action-btn" data-action-link="${a.url}">${label}</button>`;
            }
            const value = escapeHtml(a.value || a.label || '');
            return `<button type="button" class="action-btn" data-action-prompt="${value}">${label}</button>`;
        }).join('');
        return `<div class="chat-actions">${buttons}</div>`;
    }

    function createDiagnosisCard(diag) {
        const priorityColors = {
            'critical': '#DC2626',
            'high': '#EA580C',
            'medium': '#EAB308',
            'low': '#64748B'
        };
        const color = priorityColors[diag.priority] || '#164227';

        let locationOptions = campusLocations.map(loc => `
            <option value="${loc.id}" ${loc.id === diag.location_id ? 'selected' : ''}>
                ${loc.campus_name.split('(')[0]} • ${loc.building_name} (${loc.floor})
            </option>
        `).join('');

        if (!locationOptions) {
            locationOptions = `<option value="1">Main Campus • Academic Block A (Engineering)</option>`;
        }

        const cardId = 'diag-' + Date.now();

        return `
            <div id="${cardId}" style="margin-top: 14px; background: #F8FAF8; border: 1px solid #C8E6C9; border-radius: 12px; padding: 16px; color: #111827;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #E2E8F0; padding-bottom: 8px;">
                    <div style="font-size: 0.8125rem; font-weight: 700; color: #14532D; text-transform: uppercase;">
                        ⚡ 1-Click Ticket Dispatch Ready
                    </div>
                    <span style="font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 12px; background: ${color}; color: white; text-transform: uppercase;">
                        ${diag.priority}
                    </span>
                </div>

                <div style="margin-bottom: 10px;">
                    <label style="display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #4B5563; margin-bottom: 3px;">
                        Issue Title:
                    </label>
                    <input type="text" class="quick-title" value="${diag.title}" style="width: 100%; padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; font-weight: 600;">
                </div>

                <div style="margin-bottom: 10px;">
                    <label style="display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #4B5563; margin-bottom: 3px;">
                        Campus Building & Floor:
                    </label>
                    <select class="quick-location" style="width: 100%; padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px; background: white;">
                        ${locationOptions}
                    </select>
                </div>

                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #4B5563; margin-bottom: 3px;">
                        Exact Spot / Room:
                    </label>
                    <input type="text" class="quick-spot" value="${diag.specific_spot || 'Reported via DSU EcoBot'}" style="width: 100%; padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px;">
                </div>

                <div style="display: flex; gap: 8px; align-items: center; justify-content: space-between;">
                    <span style="font-size: 12px; font-weight: 700; color: #16A34A;">
                        <i class="bi bi-star-fill"></i> +50 Green Points
                    </span>
                    <button type="button" class="btn btn-primary btn-sm btn-submit-quick-ticket" style="padding: 7px 16px; font-size: 12px; border-radius: 8px;">
                        <i class="bi bi-send-check-fill"></i> Submit Official Ticket Now
                    </button>
                </div>

                <div class="quick-ticket-status" style="display: none; margin-top: 10px; font-size: 12px; padding: 10px; border-radius: 6px;"></div>
            </div>
        `;
    }

    function setupQuickTicketHandler(container, diag) {
        const btn = container.querySelector('.btn-submit-quick-ticket');
        const statusBox = container.querySelector('.quick-ticket-status');

        if (!btn) return;

        btn.addEventListener('click', () => {
            const titleInput = container.querySelector('.quick-title');
            const locSelect = container.querySelector('.quick-location');
            const spotInput = container.querySelector('.quick-spot');

            btn.disabled = true;
            btn.innerHTML = '<i class="bi bi-arrow-repeat" style="animation: spin 1s linear infinite;"></i> Registering Ticket...';

            fetch('/api/assistant/quick-report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: titleInput ? titleInput.value : diag.title,
                    description: diag.description,
                    category: diag.category,
                    priority: diag.priority,
                    location_id: locSelect ? parseInt(locSelect.value) : diag.location_id,
                    specific_spot: spotInput ? spotInput.value : diag.specific_spot,
                    is_anonymous: 0
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    btn.style.display = 'none';
                    if (statusBox) {
                        statusBox.style.display = 'block';
                        statusBox.style.background = '#DCFCE7';
                        statusBox.style.color = '#14532D';
                        statusBox.style.border = '1px solid #86EFAC';
                        statusBox.innerHTML = `
                            <strong>🎉 Success! Ticket ${data.report_number} Registered!</strong><br>
                            Campus facilities technicians have been routed. You earned <strong>+50 Green Points</strong>.<br>
                            <a href="/reports/${data.report_id}" style="display: inline-block; margin-top: 6px; font-weight: 700; color: #166534; text-decoration: underline;">
                                View Official Ticket Timeline &rarr;
                            </a>
                        `;
                    }
                } else {
                    btn.disabled = false;
                    btn.textContent = 'Retry Submission';
                    alert(data.message || 'Error creating ticket');
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.textContent = 'Retry Submission';
                console.error("Quick report error:", err);
            });
        });
    }

    function appendTypingIndicator() {
        const id = 'typing-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'chat-message bot-message typing-indicator';
        div.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="msg-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
        `;
        messagesBox.appendChild(div);
        messagesBox.scrollTop = messagesBox.scrollHeight;
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function renderSuggestions(suggestions) {
        suggestionsBox.innerHTML = suggestions
            .map(s => `<button type="button" class="suggestion-pill">${s}</button>`)
            .join('');
    }
});
