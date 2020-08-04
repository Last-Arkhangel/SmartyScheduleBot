function update_request_hours_chart(){

  var request = new XMLHttpRequest();

  request.open('GET','/fl/last_hours_statistics',true);
  request.addEventListener('readystatechange', function() {

    if ((request.readyState==4) && (request.status==200)) {

    ////////////////////////////////////////////////////////////////////
      response = JSON.parse(request.responseText);

var ctx = document.getElementById("requests-on-hours");
ctx.height = 110;
var myChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: response.data.labels,
    datasets: [{
        data: response.data.stats_data.today,
        label: "Сьогодні",
        borderColor: "#00ced1",
        fill: false
      },
      {
        data: response.data.stats_data.yesterday,
        label: "Вчора",
        borderColor: "#00ff7f",
        fill: false
      },
      {
        data: response.data.stats_data.two_days_ago,
        label: "Позавчора",
        borderColor: "#e894e8",
        fill: false
      }
    ]
  },
  options: {
    legend: { display: true },
    title: {
      display: true,
      text: 'Запити по годинам'
    }
  }
});

      ////////////////////////////////////////////////////////////////////

        }
    });

request.send();
}

//window.onload = function() {
  update_request_hours_chart();
  //setInterval(update_request_types_chart, 15000);
//}
