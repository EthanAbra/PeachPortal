const chunk_size = 64 * 1024;
var files = [];
var unsplitfiles = [];
var socketio = io();
// console.log(socketio)
// file drop handling
var dropzone = document.getElementById('dropzone');
var dropzoneunsplit = document.getElementById('dropzoneunsplit');

dropzoneClicker = function(filelist){
    for(var i = 0; i < filelist.length; i++) {
        filediv = document.createElement('div');
        filename = document.createElement('div');

        filename.classList.add('filename');
        filename.innerHTML = filelist[i].name;

        progress = document.createElement('div');
        progress.classList.add('file-progress');
        progress.classList.add('in-progress');

        filediv.appendChild(filename);
        filediv.appendChild(progress);


        document.getElementById('filelist').appendChild(filediv);
        files.push({
            file: filelist[i],
            progress: progress,
            done: false
        });
    }
}

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

        filediv.appendChild(filename);
        filediv.appendChild(progress);


        document.getElementById('filelist').appendChild(filediv);
        files.push({
            file: e.dataTransfer.files[i],
            progress: progress,
            done: false
        });
    }
}

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
                this.unsplit = false;
                readFileChunk(this.file, 0, chunk_size,
                    onReadSuccess.bind(this),
                    onReadError.bind(this));
            }
        }.bind(files[i]));
    }
    files = [];
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
    // console.log("ors")
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
    if (file.done && file.unsplit){
        document.getElementById('unsplitmessagelist').innerHTML +=
        '<div class="alert alert-warning" role="alert"> file ' + String(file.file.name) + ' received. server processing <div class="loader" id = "' + String(file.server_filename).replace(/\W/g,'_') + '" ><div class="duo duo1"><div class="dot dot-a"></div><div class="dot dot-b"></div></div><div class="duo duo2"><div class="dot dot-a"></div><div class="dot dot-b"></div> </div></div></div>';
        socketio.emit('write-complete-unsplit', {"serverfilename": file.server_filename, "clientfilename": String(file.file.name)}); 
    }
    else{
        document.getElementById('messagelist').innerHTML +=
        '<div class="alert alert-warning" role="alert"> file ' + String(file.file.name) + ' received. server processing <div class="loader" id = "' + String(file.server_filename).replace(/\W/g,'_') + '" ><div class="duo duo1"><div class="dot dot-a"></div><div class="dot dot-b"></div></div><div class="duo duo2"><div class="dot dot-a"></div><div class="dot dot-b"></div> </div></div></div>';
        socketio.emit('write-complete', {"serverfilename": file.server_filename, "clientfilename": String(file.file.name)}); 
    }
}

// read error callback
function onReadError(file, offset, length, error) {
    console.log('Upload error for ' + file.name + ': ' + error);
    this.progress.classList.add('error');
    this.progress.classList.remove('in-progress');    
    this.done = true;
}


socketio.on('peach processed', function(data) {
    // console.log('opp')
    var x = document.getElementById(data.serverfilename.replace(/\W/g,'_'));
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
    if(!data.ack){
        document.getElementById('messagelist').innerHTML +=
        '<div class="alert alert-danger" role="alert"> malformed peach data in file ' + String(data.clientfilename) + ' </div>';
        return
    }
    document.getElementById('messagelist').innerHTML += 
    '<div class="alert alert-success" role="alert"> peach processed in file ' + String(data.clientfilename) + '</div>';
    onProcessedPeach(data.clientfilename, data.addedId, data.teamId, data.athleteList)
})




function onProcessedPeach(clientfilename, addedId, teamId, athleteList){
    // console.log(clientfilename)
    // console.log(addedId)
    socketio.emit('valid-athletes', addedId, teamId, athleteList, function(ack, createdAthleteList){
        if(!ack){
            document.getElementById('messagelist').innerHTML += 
            '<div class="alert alert-danger" role="alert"> no athletes in file ' + String(clientfilename) + 
            '<br>Please add full names for each crew member directly under the \'CrewInfo\', then \'Name\' header </div>';
            return
        }
        for (athlete in createdAthleteList){
            document.getElementById('messagelist').innerHTML += '<div class="alert alert-success" role="alert"> created account for' + athlete + '</div>';
        }
        document.getElementById('messagelist').innerHTML += '<div class="alert alert-primary" role="alert"> View workout: <a href ="../workout?w=' + addedId + '">here</div>';
        return
    });
}



socketio.on('unsplit processed', function(data) {
    // console.log('opp')
    var x = document.getElementById(data.serverfilename.replace(/\W/g,'_'));
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
    if(!data.ack){
        document.getElementById('unsplitmessagelist').innerHTML +=
        '<div class="alert alert-danger" role="alert"> malformed peach data in file ' + String(data.clientfilename) + ' </div>';
        return
    }
    document.getElementById('unsplitmessagelist').innerHTML += 
    '<div class="alert alert-success" role="alert"> peach processed in file ' + String(data.clientfilename) + '</div>';
    onProcessedUnsplit(data.clientfilename, data.addedId, data.teamId, data.athleteList)
})

function onProcessedUnsplit(clientfilename, addedId, teamId, athleteList){
    document.getElementById('unsplitmessagelist').innerHTML += '<div class="alert alert-primary" role="alert"> Split this workout here: <a href ="../splitpieces?w=' + addedId + '">here</div>';
    return
}



dropzoneunsplit.ondragover = function(e) {
    e.preventDefault();
}


dropzoneunsplit.ondrop = function(e) {
    e.preventDefault();
    for(var i = 0; i < e.dataTransfer.files.length; i++) {

        filediv = document.createElement('div');
        filename = document.createElement('div');

        filename.classList.add('filename');
        filename.innerHTML = e.dataTransfer.files[i].name;

        progress = document.createElement('div');
        progress.classList.add('file-progress');
        progress.classList.add('in-progress');

        filediv.appendChild(filename);
        filediv.appendChild(progress);


        document.getElementById('unsplitfilelist').appendChild(filediv);
        unsplitfiles.push({
            file: e.dataTransfer.files[i],
            progress: progress,
            done: false
        });
    }
}

dropzoneunsplitClicker = function(filelist){
    for(var i = 0; i < filelist.length; i++) {
        filediv = document.createElement('div');
        filename = document.createElement('div');

        filename.classList.add('filename');
        filename.innerHTML = filelist[i].name;

        progress = document.createElement('div');
        progress.classList.add('file-progress');
        progress.classList.add('in-progress');

        filediv.appendChild(filename);
        filediv.appendChild(progress);


        document.getElementById('unsplitfilelist').appendChild(filediv);
        unsplitfiles.push({
            file: filelist[i],
            progress: progress,
            done: false
        });
    }
}


// upload button
var unsplitupload = document.getElementById('unsplitupload');
unsplitupload.onclick = function() {
    if (unsplitfiles.length == 0)
        alert('Drop some files above first!');
    for (var i = 0; i < unsplitfiles.length; i++) {
        socketio.emit('start-transfer', unsplitfiles[i].file.name, unsplitfiles[i].file.size, function(filename) {
            if (!filename) {
                // the server rejected the transfer
                onReadError.call(this, this.file, 0, 0, 'Upload rejected by server')
            }
            else {
                // the server allowed the transfer with the given filename
                this.server_filename = filename;
                this.unsplit = true
                readFileChunk(this.file, 0, chunk_size,
                    onReadSuccess.bind(this),
                    onReadError.bind(this));
            }
        }.bind(unsplitfiles[i]));
    }
    unsplitfiles = [];
}