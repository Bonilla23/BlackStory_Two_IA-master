document.getElementById('game-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    await startGame(this);
});

document.getElementById('fight-mode-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    await startFightMode(this);
});

// Fight Mode Toggle Logic
const fightModeYes = document.getElementById('fight-mode-yes');
const fightModeNo = document.getElementById('fight-mode-no');
const fightModeSection = document.getElementById('fight-mode-section');
const startGameButton = document.getElementById('start-game-button');
const startFightButton = document.getElementById('start-fight-button');

function toggleFightModeSection() {
    const detectiveModelLabel = document.querySelector('label[for="detective-model"]');
    const detectiveModelInput = document.getElementById('detective-model');

    if (fightModeYes.checked) {
        fightModeSection.style.display = 'block';
        startGameButton.style.display = 'none'; // Hide Start Game button when fight mode is active
        startFightButton.style.display = 'block'; // Show Start Fight button
        document.getElementById('game-output').style.display = 'none';
        document.getElementById('fight-output').style.display = 'block';

        // Hide detective model from main game form
        if (detectiveModelLabel) detectiveModelLabel.style.display = 'none';
        if (detectiveModelInput) detectiveModelInput.style.display = 'none';

    } else {
        fightModeSection.style.display = 'none';
        startGameButton.style.display = 'block'; // Show Start Game button when fight mode is inactive
        startFightButton.style.display = 'none'; // Hide Start Fight button
        document.getElementById('game-output').style.display = 'block';
        document.getElementById('fight-output').style.display = 'none';

        // Show detective model from main game form
        if (detectiveModelLabel) detectiveModelLabel.style.display = 'block';
        if (detectiveModelInput) detectiveModelInput.style.display = 'block';
    }
}

fightModeYes.addEventListener('change', toggleFightModeSection);
fightModeNo.addEventListener('change', toggleFightModeSection);

// Initial state
toggleFightModeSection();

async function startGame(form) {
    document.getElementById('game-output').style.display = 'block';
    document.getElementById('fight-output').style.display = 'none';

    // Ensure the correct button is disabled
    const submitButton = document.getElementById('start-game-button');
    if (submitButton) {
        submitButton.disabled = true;
    }

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    const gameOutput = document.getElementById('game-output');
    gameOutput.innerHTML = '<div class="event">Starting game...</div>';

    const response = await fetch('/start_game', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    gameOutput.innerHTML = '';

    await processStream(reader, decoder, gameOutput, submitButton, (line) => {
        if (line.trim() === '') return;
        
        const messageElement = document.createElement('div');
        // Determine class based on content
        if (line.startsWith('Generando') || line.startsWith('==') || line.startsWith('Narrador:') || line.startsWith('Detective:') || line.startsWith('Dificultad:') || line.startsWith('---') || line.startsWith('Misterio:') || line.startsWith('¡Se ha alcanzado') || line.startsWith('El Detective tiene') || line.startsWith('RESULTADO:') || line.startsWith('HISTORIA ORIGINAL:') || line.startsWith('Situación misteriosa:') || line.startsWith('Solución oculta:') || line.startsWith('SOLUCIÓN DEL DETECTIVE:') || line.startsWith('No se proporcionó') || line.startsWith('VEREDICTO DEL NARRADOR:') || line.startsWith('Veredicto:') || line.startsWith('Análisis:') || line.startsWith('El juego ha terminado')) {
            messageElement.classList.add('event');
        } else if (line.startsWith('Detective:')) {
            messageElement.classList.add('detective');
            line = line.replace('Detective: ', ''); // Remove prefix for display
        } else if (line.startsWith('Narrador:')) {
            messageElement.classList.add('narrator');
            line = line.replace('Narrador: ', ''); // Remove prefix for display
        } else if (line.startsWith('Error')) {
            messageElement.classList.add('error');
        }

        if (line === 'save_conversation') {
            const saveButton = document.createElement('button');
            saveButton.textContent = 'Save Conversation';
            saveButton.addEventListener('click', async () => {
                await fetch('/save_conversation', { method: 'POST' });
                alert('Conversation saved!');
                saveButton.disabled = true;
            });
            gameOutput.appendChild(saveButton);
            return;
        }

        messageElement.textContent = line;
        gameOutput.appendChild(messageElement);
    });
}

async function startFightMode(form) {
    document.getElementById('game-output').style.display = 'none';
    document.getElementById('fight-output').style.display = 'block';

    // Ensure the correct button is disabled based on the form context
    const submitButton = form.id === 'game-form' ? document.getElementById('start-game-button') : document.getElementById('start-fight-button');
    if (submitButton) {
        submitButton.disabled = true;
    }

    const formDataFight = new FormData(form);
    const dataFight = Object.fromEntries(formDataFight.entries());

    // Get narrator model from the main game form
    const gameForm = document.getElementById('game-form');
    const formDataGame = new FormData(gameForm);
    const dataGame = Object.fromEntries(formDataGame.entries());

    const data = {
        ...dataFight, // Contains detective_model_1 and detective_model_2
        narrator_model: dataGame.narrator_model || 'gpt-4', // Use game form's narrator, default to gpt-4
    };

    const fightConversationOutput = document.getElementById('fight-conversation-output');
    const fightSummary = document.getElementById('fight-summary');
    fightConversationOutput.innerHTML = '<div class="event">Starting fight mode...</div>';
    fightSummary.innerHTML = '';

    const response = await fetch('/start_fight', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    fightConversationOutput.innerHTML = ''; // Clear initial message once stream starts

    await processStream(reader, decoder, null, submitButton, (line) => {
        if (line.trim() === '') return;
        
        try {
            const msg = JSON.parse(line);
            const messageElement = document.createElement('div');

            if (msg.type === 'narrator') {
                messageElement.classList.add('narrator');
                messageElement.textContent = msg.content;
                fightConversationOutput.appendChild(messageElement);
            } else if (msg.type === 'detective1_question') {
                messageElement.classList.add('detective', 'detective1-question');
                messageElement.textContent = msg.content; // Removed duplicate prefix
                fightConversationOutput.appendChild(messageElement);
            } else if (msg.type === 'detective1_answer') {
                messageElement.classList.add('narrator', 'detective1-answer'); // Narrator answers detective 1
                messageElement.textContent = msg.content; // Removed duplicate prefix
                fightConversationOutput.appendChild(messageElement);
            } else if (msg.type === 'detective2_question') {
                messageElement.classList.add('detective', 'detective2-question');
                messageElement.textContent = msg.content; // Removed duplicate prefix
                fightConversationOutput.appendChild(messageElement);
            } else if (msg.type === 'detective2_answer') {
                messageElement.classList.add('narrator', 'detective2-answer'); // Narrator answers detective 2
                messageElement.textContent = msg.content; // Removed duplicate prefix
                fightConversationOutput.appendChild(messageElement);
            } else if (msg.type === 'summary') {
                const summaryItem = document.createElement('div');
                summaryItem.classList.add('fight-summary-item');
                summaryItem.innerHTML = msg.content; // Summary content is HTML
                fightSummary.appendChild(summaryItem);
            } else if (msg.type === 'error') {
                messageElement.classList.add('error');
                messageElement.textContent = `Error: ${msg.content}`;
                fightConversationOutput.appendChild(messageElement);
                fightSummary.appendChild(messageElement.cloneNode(true)); // Also show error in summary area
            } else {
                 messageElement.classList.add('event');
                 messageElement.textContent = msg.content;
                 fightConversationOutput.appendChild(messageElement);
            }
        } catch (e) {
            console.error("Failed to parse JSON for line:", line, e);
            const errorElement = document.createElement('div');
            errorElement.classList.add('error');
            errorElement.textContent = `Error processing message: ${line}`;
            fightConversationOutput.appendChild(errorElement);
        }
    });
}

async function processStream(reader, decoder, outputElement, submitButton, processLineCallback) {
    let buffer = '';
    while (true) {
        const { done, value } = await reader.read();
        if (done) {
            if (buffer) {
                processLineCallback(buffer);
            }
            submitButton.disabled = false;
            break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
            processLineCallback(line);
        }
    }
}
