const chunk_size = 64 * 1024;
var files = [];
var socketio = io();
console.log(socketio)
// file drop handling
var dropzone = document.getElementById('dropzone');
dropzone.ondragover = function(e) {
    e.preventDefault();
}
dropzone.ondrop = function(e) {
    e.preventDefault();
    for(var i = 0; i < e.dataTransfer.files.length; i++) {
        filediv = document.createElement('div');
        filename = document.createElement('div');

        filename.classList.add('filename');
        filename.innerHTML = e.dataTransfer.files[i].name;

        progress = document.createElement('div');
        progress.classList.add('file-progress');
        progress.classList.add('in-progress');

        messages = document.createElement('div');
        messages.classList.add('peach-not-processed')
        messages.classList.add('peach-processed')
        messages.classList.add('no-athletes')
        messages.classList.add('athletes-processed')

        filediv.appendChild(filename);
        filediv.appendChild(progress);


        document.getElementById('filelist').appendChild(filediv);
        document.getElementById('messagelist').appendChild(messages);
        files.push({
            file: e.dataTransfer.files[i],
            progress: progress,
            done: false
        });
    }
}

// read a chunk from a file
function readFileChunk(file, offset, length, success, error) {
    end_offset = offset + length;
    if (end_offset > file.size)
        end_offset = file.size;
    var r = new FileReader();
    r.onload = function(file, offset, length, e) {
        if (e.target.error != null)
            error(file, offset, length, e.target.error);
        else
            success(file, offset, length, e.target.result);
    }.bind(r, file, offset, length);
    r.readAsArrayBuffer(file.slice(offset, end_offset));
}

// read success callback
function onReadSuccess(file, offset, length, data) {
    console.log("ors")
    if (this.done)
        return;
    if (!socketio.connected) {
        setTimeout(onReadSuccess.bind(this, file, offset, length, data), 5000);
        return;
    }
    socketio.emit('write-chunk', this.server_filename, offset, data, function(offset, ack) {
        if (!ack)
            onReadError(this.file, offset, 0, 'Transfer aborted by server')
    }.bind(this, offset));
    end_offset = offset + length;
    this.progress.style.width = parseInt(300 * end_offset / file.size) + "px";
    if (end_offset < file.size)
        readFileChunk(file, end_offset, chunk_size,
            onReadSuccess.bind(this),
            onReadError.bind(this));
    else {                        
        this.progress.classList.add('complete');
        this.progress.classList.remove('in-progress');
        this.done = true;
        onReadComplete(this);
    }
}

function onReadComplete(file) {
    console.log(file.file.name)
    if (file.done){
        document.getElementById('messagelist').innerHTML +=
        '<div class="alert alert-warning" role="alert"> file ' + String(file.file.name) + ' received. server processing ... </div>';
        socketio.emit('write-complete', file.server_filename, function(ack, addedId, teamId, athleteList){
            if(!ack){
                document.getElementById('messagelist').innerHTML +=
                '<div class="alert alert-danger" role="alert"> malformed peach data in file ' + String(file.file.name) + ' </div>';
                return
            }
            document.getElementById('messagelist').innerHTML += 
            '<div class="alert alert-success" role="alert"> peach processed in file ' + String(file.file.name) + '</div>';
            onProcessedPeach(file, addedId, teamId, athleteList)
        })//.bind(this);
    }
}

function onProcessedPeach(file, addedId, teamId, athleteList){
    console.log("opp")
    socketio.emit('valid-athletes', addedId, teamId, athleteList, function(ack, createdAthleteList){
        if(!ack){
            document.getElementById('messagelist').innerHTML += 
            '<div class="alert alert-danger" role="alert"> no athletes in file ' + String(file.file.name) + 
            '<br>Please add full names for each crew member directly under the \'CrewInfo\', then \'Name\' header </div>';
            return
        }
        for (athlete in createdAthleteList){
            document.getElementById('messagelist').innerHTML += '<div class="alert alert-success" role="alert"> created account for' + athlete + '</div>';
        }
        // TODO: Would you like to view this workout? with href
        document.getElementById('messagelist').innerHTML += '<div class="alert alert-primary" role="alert"> View workout: <a href ="../workout?w=' + addedId + '">here</div>';
        return
    });
}




// read error callback
function onReadError(file, offset, length, error) {
    console.log('Upload error for ' + file.name + ': ' + error);
    this.progress.classList.add('error');
    this.progress.classList.remove('in-progress');    
    this.done = true;
}

// upload button
var upload = document.getElementById('upload');
upload.onclick = function() {
    if (files.length == 0)
        alert('Drop some files above first!');
    for (var i = 0; i < files.length; i++) {
        socketio.emit('start-transfer', files[i].file.name, files[i].file.size, function(filename) {
            if (!filename) {
                // the server rejected the transfer
                onReadError.call(this, this.file, 0, 0, 'Upload rejected by server')
            }
            else {
                // the server allowed the transfer with the given filename
                this.server_filename = filename;
                readFileChunk(this.file, 0, chunk_size,
                    onReadSuccess.bind(this),
                    onReadError.bind(this));
            }
        }.bind(files[i]));
    }
    files = [];
}