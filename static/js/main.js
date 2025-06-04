function sendRequest(url, method, data, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function() {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            if (xhr.status === 200) {
                callback(null, xhr.responseText);
            } else {
                callback('Error: ' + xhr.status);
            }
        }
    };
    xhr.send(JSON.stringify(data));
}

function handleSubmit(event, url) {
    event.preventDefault();

    var form = event.target;
    var formData = new FormData(form);
    var data = {};
    formData.forEach(function(value, key) {
        data[key] = value;
    });

    sendRequest(url, 'POST', data, function(err, response) {
        // Use closest() to find the container that holds the form and the result-message element
        var container = form.closest('.container');
        var messageElem = container ? container.querySelector('.result-message') : null;
        
        if (err) {
            if (messageElem) {
                messageElem.innerHTML = 'An error occurred. Please try again.';
            }
            return;
        }
        
        var result = JSON.parse(response);
        if (result.success) {
            if (result.redirect) {
                // If redirect is provided, navigate away.
                window.location.href = result.redirect;
            } else if (messageElem) {
                // Otherwise, update the message element with the returned message.
                messageElem.innerHTML = result.message;
            }
        } else {
            if (messageElem) {
                messageElem.innerHTML = result.message;
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    var forms = document.getElementsByTagName('form');
    for (var i = 0; i < forms.length; i++) {
        forms[i].addEventListener('submit', function(event) {
            handleSubmit(event, this.action);
        });
    }
});
