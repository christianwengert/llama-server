import hljs from "highlight.js";
import 'highlight.js/styles/github.css';


const scrollToBottom = () => {
    let messages = document.getElementById("chat")!
    messages.scrollTo(0, messages.scrollHeight);
}


const renderMessage = (message: string, direction: 'me' | 'them', chat: HTMLElement): string => {
    const ident = (Math.random() + 1).toString(36).substring(2);
    const m = `
    <div class="message from-${direction}" id="${ident}">
        <div class="inner-message">${message}</div>
    </div>`
    chat.insertAdjacentHTML('beforeend', m);
    return ident;
};

const setupModelChange = () => {
    let modelChangeSelect = document.getElementById('model-change') as HTMLSelectElement;
    if(!modelChangeSelect) {
        return;
    }
    const url = new URL(document.location.href)

    modelChangeSelect!.addEventListener('change', ()=> {
        document.location = url.pathname + '?' + new URLSearchParams({
            model: modelChangeSelect.value
        })
    })
    const p = new URLSearchParams(document.location.search)
    if (p.get('model')) {
        modelChangeSelect.value = p.get('model') || ""
    }
};


const setFocusToInputField = (textInput: HTMLDivElement) => {
    setTimeout(() => {
        textInput.focus()
    }, 100)
};

const setupTranslation = () => {
    const url = new URL(document.location.href)
    if(url.pathname != '/translate') {
        return
    }

    const fileInput = document.getElementById('file') as HTMLInputElement;
    if(!fileInput) {
        return
    }

    fileInput.addEventListener('change', (e) => {

        fileInput.disabled = true;

        const input = e.target as HTMLInputElement;
        const files = input.files!;
        const file = files[0]
        let formData= new FormData();
        formData.append('file', file);
        const name = file.name;
        formData.append('name', name);

        const stopButton = document.getElementById('stop-generating')! as HTMLButtonElement;
        stopButton.disabled = false;

        const chat = document.getElementById('chat')!;
        const ident = renderMessage('', 'them', chat)
        const elem = document.getElementById(ident)!;
        let modelChangeSelector = document.getElementById('model-change')! as HTMLSelectElement
        const inner = elem.querySelector('.inner-message')! as HTMLElement;
        inner.innerHTML = '<div class="loading"></div>'

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/translate');

        let seenBytes= 0;
        xhr.onreadystatechange = function () {

            if (xhr.readyState == 3) {  // streaming
                const newData = xhr.response.substring(seenBytes);
                if (inner.querySelector('.loading')) {
                    inner.innerHTML = "";
                }
                inner.innerHTML += newData;
                seenBytes = xhr.responseText.length;
            }
            if (xhr.readyState == 4) {  // done
                modelChangeSelector.disabled = false;
                fileInput.disabled = false;
                stopButton.disabled = true;
                scrollToBottom()
            }
        };

        xhr.addEventListener("error", function (e) {
            console.log("error: " + e);
        });
        // xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
        // xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
        xhr.send(formData);













        // fetch("/translate",
        //     {
        //         body: formData,
        //         method: "post"
        //     }).then(()=> {
        //         window.location.href = '/embeddings/' + name;
        //
        // });
    })
};

const run = () => {
    setupModelChange();
    setupPdfUpload();
    setupCodeUpload();
    setupSQLUpload();
    checkEmbeddings();
    setupTranslation();

    const chat = document.getElementById('chat')!;

    // todo: We cannot stop generation yet
    const stopButton = document.getElementById('stop-generating')! as HTMLButtonElement;
    if(stopButton) {
        stopButton.addEventListener('click', (e) => {
            e.preventDefault();
            fetch('/cancel').then(()=>{})
            stopButton.disabled = true;
        })
    }


    const resetButton = document.getElementById('reset-button') as HTMLElement;
    if(resetButton) {
        resetButton.addEventListener('click', (e) => {
            e.preventDefault();
            fetch('/reset').then(() => {
                document.location.reload()
            })
        })
    }



    const textInput = document.getElementById('input-box')! as HTMLDivElement;
    let modelChangeSelector = document.getElementById('model-change')! as HTMLSelectElement
    if (!modelChangeSelector) {
        modelChangeSelector = document.getElementById('embeddings-change')! as HTMLSelectElement
    }

    setFocusToInputField(textInput);

    textInput.addEventListener('keypress', handleInput)

    function handleInput(e: KeyboardEvent) {
        if (e.key === 'Enter' && e.shiftKey === false) {
            e.preventDefault();
            const m = textInput.innerText;
            renderMessage(textInput.innerText, 'me', chat);
            textInput.innerText = '';
            textInput.contentEditable = "false";
            stopButton.disabled = false;
            modelChangeSelector.disabled = true

            const ident = renderMessage('', 'them', chat)
            const elem = document.getElementById(ident)!;
            const inner = elem.querySelector('.inner-message')! as HTMLElement;
            inner.innerHTML = '<div class="loading"></div>'

            scrollToBottom()

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/');

            let seenBytes = 0;
            xhr.onreadystatechange = function () {

                if (xhr.readyState == 3) {  // streaming
                    const newData = xhr.response.substring(seenBytes);
                    if (inner.querySelector('.loading')) {
                        inner.innerHTML = "";
                    }
                    inner.innerHTML += newData;
                    seenBytes = xhr.responseText.length;
                }
                if (xhr.readyState == 4) {  // done
                    textInput.contentEditable = "true";
                    stopButton.disabled = true;
                    modelChangeSelector.disabled = false;
                    // adapt markdown for ```
                    const pattern = /```([a-z]+)? ?([^`]*)```/g
                    const rep = `<div class="code-header"><div class="language">$1</div><div class="copy">Copy</div></div><pre><code class="language-$1">$2</code></pre>`
                    const intermediate = inner.innerText.replace(pattern, rep)
                    // adapt markdown for `
                    const pattern2 = /`([^`]*)`/g
                    const rep2 = `<code class="inline">$1</code>`
                    inner.innerHTML = intermediate.replace(pattern2, rep2)

                    scrollToBottom()
                    // highlight code
                    inner.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(<HTMLElement>block);
                    });
                    // set up copy to clipboard buttons
                    inner.querySelectorAll('.code-header >.copy').forEach((copyElem) => {
                        copyElem.addEventListener('click', (copyEvent) => {
                            copyEvent.preventDefault();
                            const target = copyEvent.target! as HTMLElement;

                            const t = (target.parentElement!.nextElementSibling! as HTMLElement).innerText;
                            // Copy the text inside the text field
                            navigator.clipboard.writeText(t).then(() => {
                            });
                            target.innerText = 'Copied'
                            target.style.cursor = 'auto'

                            setInterval(() => {
                                target.innerText = 'Copy'
                                target.style.cursor = 'pointer'

                            }, 3000)
                        })
                    })

                    textInput.focus()
                }
            };

            xhr.addEventListener("error", function (e) {
                console.log("error: " + e);
            });
            xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
            xhr.send(JSON.stringify({'input': m, 'model': modelChangeSelector.value}));
        }
    }
};

const checkEmbeddings = () => {

    const dialog = document.querySelector('#wait')! as HTMLDialogElement;

    function openDialog() {
        if(dialog.attributes.hasOwnProperty('open')) {
            return
        }
        dialog.showModal();
    }
    function closeDialog() {
        if(dialog.attributes.hasOwnProperty('open')) {
            dialog.close();
        }
    }

    let clearFun: number;

    const [_empty, path1, path2] = new URL(document.location.href).pathname.split('/')
    const fn = () => {
        fetch('/check/' + path2).then(response => response.text()).then((data) => {
            // console.log(data)
            if(data === 'RUNNING') {
                openDialog()
                dialog.innerText = "Please wait"
            } else if(data === 'OK') {
                closeDialog();
                clearInterval(clearFun);
            } else {
                closeDialog();
                console.warn('Got nothing')
                clearInterval(clearFun);
            }
        })

    }
    if(path1 === 'embeddings' && path2) {
        fn();
        clearFun = setInterval(fn, 1000)
    }
}
const setupPdfUpload = () => {
    const form = document.getElementById('upload-pdf') as HTMLFormElement;

    if(!form) {
        return;
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault()
        const file = document.getElementById('pdf-file')! as HTMLInputElement;

        let formData = new FormData();
        formData.append('file', file.files![0]);
        const name = file.files![0].name;
        formData.append('name', name);
        formData.append('embedding', 'pdf');

        fetch("/upload",
            {
                body: formData,
                method: "post"
            }).then(()=> {
                window.location.href = '/embeddings/' + name;

        });
    })
}


const setupSQLUpload = () => {
    const form = document.getElementById('upload-sql')! as HTMLFormElement;
    if(!form) {
        return;
    }
    form.addEventListener('submit', (e) => {
        e.preventDefault()
        const file = document.getElementById('sql-file')! as HTMLInputElement;

        let formData = new FormData();
        formData.append('file', file.files![0]);
        const name = file.files![0].name;
        formData.append('name', name);
        formData.append('embedding', 'sql');

        fetch("/upload",
            {
                body: formData,
                method: "post"
            }).then(()=> {
                window.location.href = '/embeddings/' + name;

        });
    })
}


const setupCodeUpload = () => {
    const form = document.getElementById('upload-code')! as HTMLFormElement;
    if(!form) {
        return;
    }
    form.addEventListener('submit', (e) => {
        e.preventDefault()
        const file = document.getElementById('code-folder')! as HTMLInputElement;
        const name = document.getElementById('code-jobname')! as HTMLInputElement;

        let formData = new FormData();
        // formData.append('file', file.files![0]);
        // ar data = new FormData()
        for (const f of file.files!) {
          formData.append('file', f);
        }
        // const name = file.files![0].name;
        formData.append('name', name.value);
        formData.append('embedding', 'code');

        fetch("/upload",
            {
                body: formData,
                method: "post"
            }).then(()=> {
                window.location.href = '/embeddings/' + name.value;
        });
    })
}

const setupSwitchEmbedding = () => {
    const embeddingsChanger = document.getElementById('embeddings-change') as HTMLSelectElement
    if (!embeddingsChanger) {
        return;
    }

    embeddingsChanger.addEventListener('change', (e) => {
        if(embeddingsChanger.value) {
            document.location.href = '/embeddings/' + embeddingsChanger.value;
        }
    })
}


setupSwitchEmbedding()

run()



