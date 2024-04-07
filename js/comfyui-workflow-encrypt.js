import {app} from "../../scripts/app.js";
import {api} from "../../scripts/api.js"
import {$el} from "../../scripts/ui.js";

app.registerExtension({
    name: "Comfy.WorkflowEncryptMenu",
    init() {
        $el("style", {
            textContent: style,
            parent: document.head,
        });
    },
    async setup() {
        let orig_clear = app.graph.clear;
        app.graph.clear = function () {
            orig_clear.call(app.graph);
        };

        const menu = document.querySelector(".comfy-menu");
        const separator = document.createElement("hr");

        separator.style.margin = "20px 0";
        separator.style.width = "100%";
        menu.append(separator);

        const saveButton = document.createElement("button");

        saveButton.textContent = "Save(Encrypted)";
        saveButton.onclick = () => {
            app.graphToPrompt()
                .then(prompt => {
                    const workflow = prompt['workflow']

                    api.fetchApi(`/workflow_encrypt/save_encrypt_method`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            workflow: workflow
                        })
                    }).then(response => response.json())
                        .then(async data => {
                            alert(data['key']);

                            const encryptedData = data['encrypted_data'];

                            const blob = new Blob([encryptedData], {type: 'text/plain'});

                            const url = URL.createObjectURL(blob);

                            const anchor = document.createElement('a');
                            anchor.href = url;
                            anchor.download = 'encrypted_data.txt';

                            document.body.appendChild(anchor);

                            anchor.click();

                            document.body.removeChild(anchor);
                            URL.revokeObjectURL(url);
                        });
                });
        }
        menu.append(saveButton);

        const loadButton = document.createElement("button");

        loadButton.textContent = "Load(Decrypted)";
        loadButton.onclick = () => {
            const decryptedKey = prompt("Please enter decrypted key:");

            if (decryptedKey !== null) {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.onchange = e => {
                    const files = e.target.files;
                    if (files.length === 0) return;

                    const file = files[0];
                    const reader = new FileReader();

                    reader.onload = loadEvent => {
                        const fileContent = loadEvent.target.result;
                        api.fetchApi('/workflow_encrypt/load_decrypted_method', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                decryptedKey: decryptedKey,
                                fileContent: fileContent
                            })
                        }).then(response => response.json())
                            .then(async data => {
                                if ('status' in data) {
                                    alert(data['status']);
                                } else {
                                    await app.loadGraphData(data);
                                }
                            });
                    };

                    reader.readAsText(file);
                };

                fileInput.click();
            } else {
                console.log("User cancelled the prompt.");
            }
        }
        menu.append(loadButton);
    }
});
