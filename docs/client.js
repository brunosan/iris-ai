function el(x) {
  element = document.getElementById(x)
  if (element === null) {
    console.log("return dummy element, no id: ", x);
    return document.createElement("div")
  } else {
    return element
  }
}

var max_side_px = 256
var quality = 0.8
var server = "https://gh3phbuesj.execute-api.us-east-1.amazonaws.com/Prod/invocations/"
//var server = "http://localhost:3000/invocations"

var spinner = '<div class="spinner-border spinner-border-sm" role="status"><span class="sr-only">Loading...</span></div>'

var n_samples = 5

var old_rand = -1
function rand_img(n_samples) {
  var rand = Math.ceil(Math.random() * (n_samples));
  if ( rand == old_rand ) rand = Math.ceil(Math.random() * (n_samples));
  old_rand = rand;
  return "assets/sample" + rand + ".jpg"
};

function wake_up_aws_lambda(){
  console.log("Making 'ping' call to trigger cold-start: Ping...");
  var xhr = new XMLHttpRequest();
  xhr.open('POST', server , true);
  xhr.onerror = function(e) {
    console.log("Error on respone",xhr.responseText,e);
  }
  xhr.onload = function(e) {
    if (this.readyState === 4) {
      var response = e.target.responseText;
      console.log("Pong received. App ready. Response:", response);
    }
  }
  xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
  var params = 'ping';
  xhr.send(params);
}

wake_up_aws_lambda();
el("sample1").src = rand_img(n_samples);
el("sample2").src = rand_img(n_samples);

function get_size(x, y, max_side_px) {
  //reduce the new dimensions keeping aspect ratio
  major_side = Math.max(x, y);
  if (major_side < max_side_px) {
    return [x, y]
  } else {
    r = max_side_px / major_side
    return [
      Math.round(x * r),
      Math.round(y * r)
    ];
  }
}

function showPicker(inputId) {
  el('tos').className = el('tos').className + " no-display "
  el('userpicker').click();
  //addCard();
}

function showTos() {
  alert("We only upload a small version of the image so we can do our predictions. We might keep it only so we can improve our AI. No other information about the user is stored. More info data@brunosan.eu");
};


function addCard() {
  var newcard = $("#card-template").clone()
  el('lastImgPlaceholder').className = el('lastImgPlaceholder').className + " no-display "
  $("#card-template").removeAttr('id')
  $("#card-row").append(newcard);
}

function selectImg(value) {
  id = "userimg"
  el(id).src = value;
  el(id).className = el(id).className.replace(/no-display/g, "")
  el("ImgPlaceholder").className = el("ImgPlaceholder").className.replace(/no-display/g, "")
  el("lastImgPlaceholder").className = " no-display ";
  var preview = el(id);
  var file = el('userpicker').files[0];
  var reader = new FileReader();

  reader.addEventListener("load", function() {
    preview.src = reader.result;
  }, false);

  if (file) {
    reader.readAsDataURL(file);
  }
  analyzeImg(id,file);
  el(id).className = el(id).className.replace(/no-display/g, "")
}

function analyzeImg(input,file) {
  el('tos').className = el('tos').className + " no-display "
  el(id + '-label2').className = el(id + '-label2').className + " no-display "
  console.info("analyzeImg",input);
  id = input.split("-")[0];

  var reader = new FileReader();
  reader.onload = function(e) {
    var image = new Image();
    //compress Image
    image.onload = function() {
      var canvas = document.createElement("canvas");
      var context = canvas.getContext("2d");
      var new_size = get_size(image.width, image.height, max_side_px);
      [canvas.width, canvas.height] = new_size;
      context.drawImage(image, 0, 0, image.width, image.height, 0, 0, canvas.width, canvas.height);
      console.log("Converted");

      el(id).src = canvas.toDataURL("image/jpeg", quality);
      analyze(id)
    };
    image.src = e.target.result;
  };
  el("userimgdiv").className = el("userimgdiv").className.replace(/no-display/g, "")
  reader.readAsDataURL(file);

}

function dataURItoBlob(dataURI) {
  // convert base64/URLEncoded data component to raw binary data held in a string
  var byteString;
  if (dataURI.split(',')[0].indexOf('base64') >= 0)
    byteString = atob(dataURI.split(',')[1]);
  else
    byteString = unescape(dataURI.split(',')[1]);

  // separate out the mime component
  var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];

  // write the bytes of the string to a typed array
  var ia = new Uint8Array(byteString.length);
  for (var i = 0; i < byteString.length; i++) {
    ia[i] = byteString.charCodeAt(i);
  }

  return new Blob([ia], {type: mimeString});
}

const toDataURL = url => fetch(url)
  .then(response => response.blob())
  .then(blob => new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  }))

function analyzeSample(input){
  el('tos').className = el('tos').className + " no-display "
  id = input.id.split("-")[0];
  sampleImg = el(id);
  toDataURL(sampleImg.src)
  .then(dataUrl => {
    sampleImg.src = dataUrl;
    analyze(id,skip_upload = true)
  })
}

function analyze(input, skip_upload = false) {
  id = input.split("-")[0];
  var uploadFiles = el(id).src;

  el(id + '-label').innerHTML = 'Uploading ...' + spinner;
  el(id + '-label').className = el(id + '-label').className.replace(/no-display/g, "")
  //el(id + '-button').remove()

  var xhr = new XMLHttpRequest();
  var loc = window.location
  xhr.open('POST', server , true);
  xhr.onerror = function(e) {
    console.log("Error on respone",xhr.responseText,e);
    el(id + '-label').innerHTML = `Error :-(`;
    //el(id + '-label').className = el(id + '-label').className + " no-display "
  }
  xhr.onload = function(e) {
    if (this.readyState === 4) {
      var response = JSON.parse(e.target.responseText);
      console.log("Response:", response);
      el(id + '-label').innerHTML = "Result = "+response['summary'].toString();
      if (Object.keys(response['others']).length === 0){
        el(id + '-label2').className = el(id + '-label2').className + " no-display "
      } else {
        el(id + '-label2').className = el(id + '-label2').className.replace(/no-display/g, "")
        console.log(id,JSON.stringify(response['others']));
        el(id + '-label2').innerHTML = "Alternatives: "+JSON.stringify(response['others']).split(",").join("\n");
      }
    }
  }

  xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
  var params = '{"url":"'+uploadFiles+'"}';
  xhr.send(params);
}
