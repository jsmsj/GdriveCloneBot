function timeDifference(current, previous) {
  var msPerMinute = 60 * 1000;
  var msPerHour = msPerMinute * 60;
  var msPerDay = msPerHour * 24;
  var msPerMonth = msPerDay * 30;
  var msPerYear = msPerDay * 365;

  var elapsed = current - previous;
  var tsmsg = "";

  if (elapsed < msPerMinute) {
    tsmsg = Math.round(elapsed / 1000) + " seconds ago";
  } else if (elapsed < msPerHour) {
    tsmsg = Math.round(elapsed / msPerMinute) + " minutes ago";
  } else if (elapsed < msPerDay) {
    tsmsg = Math.round(elapsed / msPerHour) + " hours ago";
  } else if (elapsed < msPerMonth) {
    tsmsg = Math.round(elapsed / msPerDay) + " days ago";
  } else if (elapsed < msPerYear) {
    tsmsg = Math.round(elapsed / msPerMonth) + " months ago";
  } else {
    tsmsg = Math.round(elapsed / msPerYear) + " years ago";
  }
  if (tsmsg.startsWith("1 ")) tsmsg = tsmsg.replace("s ago", " ago");
  return tsmsg;
}


const arrayReverseObj = (obj) => {
  let newArray = []

  Object.keys(obj)
    // .sort()
    .reverse()
    .forEach(key => {
      // console.log(key)
      newArray.push( {
      'key':key,
      'value':obj[key]
      })
    })

  // console.log(newArray)
  return newArray  
}

function timeConverter(UNIX_timestamp){
  var a = new Date(UNIX_timestamp * 1000);
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var year = a.getFullYear();
  var month = months[a.getMonth()];
  var date = a.getDate();
  var hour = a.getHours();
  var min = a.getMinutes() < 10 ? '0' + a.getMinutes() : a.getMinutes();
  var sec = a.getSeconds() < 10 ? '0' + a.getSeconds() : a.getSeconds();
  var time = date + ' ' + month + ' ' + year + ' ' + hour + ':' + min + ':' + sec ;
  return time;
}


window.onload = async function () {
  const data = arrayReverseObj(await fetch("https://raw.githubusercontent.com/jsmsj/GdriveCloneBot/master/changelog.json").then((e) => e.json()));
  // console.log(data);
  var main = document.getElementById("maingrid");
  let j = 1
  for (let i in data) {
    let daa = data[i].value;
    let elem = document.createElement("div");
    elem.className = "row justify-content-center m-2 fs-5";
    elem.innerHTML = `<div class="col-1 h4">${j}.</div>\n<div class="col-3 h4">${daa.title}</div>\n<div class="col">${daa.description}</div>\n<div class="col-3 text-end">${timeConverter(parseInt(daa.timestamp))}<br><span class="text-bg-light rounded px-1">${timeDifference(Date.now(), daa.timestamp * 1000)}</span></div>`;
    main.appendChild(elem);
    j++
  }
};