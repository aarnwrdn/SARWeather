$(document).ready(function () {
    const delayPrediction = 2 * 60 * 1000 // 60 * 60 * 1000 ms (1 hour)
    const delayMonitoring = 10 * 1000 // 20 * 1000 ms (20 seconds)
    const delayHistory = 60 * 60 * 1000 // 60 * 60 * 1000 ms (1 hour)

    const tablePrediction = document.getElementById('table-prediction')
    if (tablePrediction != null) {
        updateDataPrediction()
        setInterval(updateDataPrediction, delayPrediction)
    }

    const monitoringData = document.getElementById('monitoring-data')
    if (monitoringData != null) {
        updateDataMonitoring()
        setInterval(updateDataMonitoring, delayMonitoring)
    }

    const historyData = document.getElementById('table-history')
    if (historyData != null) {
        updateDataHistory()
        setInterval(updateDataHistory, delayHistory)
    }

    $('#refresh').click(function () {
        if (historyData != null) {
            updateDataHistory()
        }
        if (tablePrediction != null) {
            updateDataPrediction()
        }
        if (monitoringData != null) {
            updateDataMonitoring()
        }
    });

    function updateDataMonitoring() {
        $('#monitoring-data .card-text').each(function () {
            $(this).addClass('placeholder-glow')
            $(this).html(`
                <span class="placeholder col-6"></span>
            `)
        })

        $.get('/data/latest', function (data) {
            $('#monitoring-data .card-text').each(function () {
                let id = $(this).attr('id')

                if (id == "WindDirection") {
                    data[id] = classifyWindDir(data[id])
                }

                $(this).text(data[id] ?? "N/A")
                $(this).removeClass('placeholder-glow')
            })

        }).fail(function () {
            $('#alert').removeClass('d-none')
            $('#alert').addClass('show')

            $('#monitoring-data .card-text').each(function () {
                $(this).html("N/A")
                $(this).removeClass('placeholder-glow')
            })
        })
    }


    function updateDataPrediction() {
        // only run if data-time is null or if current time (hour) is greater than data-time (hour)
        const attribute = tablePrediction.getAttribute('data-time')
        let tableElement = $('#table-prediction tbody')
        let currentTime = new Date()
        let currentHour = currentTime.getHours();

        if (attribute != null || currentHour > attribute || currentHour === 0) {
            $(tableElement).html(`
                            <tr>
                                <td colspan="8" class="text-center">
                                    <div class="spinner-border" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </td>
                            </tr>
                        `)
            $.get('/predict', function (datas) {
                if (datas.length > 0) {
                    let tableContent = ''
                    datas.forEach(data => {
                        tableContent += '<tr>'
                        tableContent += '<td>' + data['timestamp'] + '</td>'
                        tableContent += '<td>' + data['rainfall_text'] + '</td>'
                        tableContent += '<td>' + data['TEMP'] + '</td>'
                        tableContent += '<td>' + data['HUMIDITY'] + '</td>'
                        tableContent += '<td>' + data['PRESSURE'] + '</td>'
                        tableContent += '<td>' + data['RAINFALL'] + '</td>'
                        tableContent += '<td>' + data['WINDSPEED'] + '</td>'
                        tableContent += '<td>' + data['winddir_text'] + '</td>'
                        tableContent += '</tr>'
                    });

                    tableElement.html(tableContent)

                    let firstTimestamp = tsGetHours(datas[0]['ts'])
                    tableElement.attr('data-time', firstTimestamp)

                    // remove alert
                    $('.alert').removeClass('show')
                    $('.alert').addClass('d-none')
                }
            }).fail(function () {
                $('#alert').removeClass('d-none')
                $('#alert').addClass('show')

                $('#table-prediction tbody').html(`
                    <tr>
                        <td colspan="8">Gagal memperbarui data</td>
                    </tr>
                `)
            })
        }
    }

    function updateDataHistory() {
        // remove inside of container-table
        const containerTable = document.getElementById('container-table')
        containerTable.innerHTML = `                        
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                Memperbarui data ...
            `
        $.get('/data/history', function (datas) {
            let tableElement = $(containerTable)
            const tableHeader = `
                            <thead>
                                <tr>
                                    <th data-type="date" data-format="DD/MM/YYYY HH:mm:ss">Waktu</th>
                                    <th>Suhu</th>
                                    <th>Kelembaban</th>
                                    <th>Tekanan Udara</th>
                                    <th>Curah Hujan</th>
                                    <th>Kecepatan Angin</th>
                                    <th>Arah Angin</th>
                                    <th>Latitude</th>
                                    <th>Longitude</th>
                                </tr>
                            </thead>
                        `;

            let tableContent = '<tbody>'
            datas.forEach(data => {
                tableContent += '<tr>'
                tableContent += '<td>' + tsToDate(data['TS']) + '</td>'
                tableContent += '<td>' + data['Temperature'] + '</td>'
                tableContent += '<td>' + data['Humidity'] + '</td>'
                tableContent += '<td>' + data['Pressure'] + '</td>'
                tableContent += '<td>' + data['Rainfall'] + '</td>'
                tableContent += '<td>' + data['WindSpeed'] + '</td>'
                tableContent += '<td>' + classifyWindDir(data['WindDirection']) + '</td>'
                tableContent += '<td>' + data['Latitude'] + '</td>'
                tableContent += '<td>' + data['Longitude'] + '</td>'
                tableContent += '</tr>'
            });

            tableContent += '</tbody>'

            tableElement.html(`
                                <table id="table-history">
                                    ${tableHeader}
                                    ${tableContent}
                                </table>
                            `)

            const tableHistory = document.getElementById('table-history')
            new simpleDatatables.DataTable(tableHistory, {
                paging: true,
                perPageSelect: [10, 25, 50, ["All", -1]],
                columns: [
                    {
                        data: 'TS',
                        render: function (data, type, row) {
                            if (type === 'display' || type === 'filter') {
                                return tsToDate(data);
                            }
                            return data;
                        }
                    },
                    { data: 'Temperature' },
                    { data: 'Humidity' },
                    { data: 'Pressure' },
                    { data: 'Rainfall' },
                    { data: 'WindSpeed' },
                    { data: 'WindDirection' },
                    { data: 'Latitude' },
                    { data: 'Longitude' }
                ],
                columnDefs: [{
                    type: "date",
                    targets: [0]
                }]
            });

        }).fail(function () {
            containerTable.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        Gagal memperbarui data
                    </div>
                `
        })
    }

    // convert ts to date
    function tsToDate(ts) {
        let date = new Date(ts)
        let day = date.getDate()
        let month = date.getMonth() + 1
        let year = date.getFullYear()
        let hour = date.getHours()
        let minute = date.getMinutes()
        let second = date.getSeconds()
        day = day < 10 ? '0' + day : day
        month = month < 10 ? '0' + month : month
        hour = hour < 10 ? '0' + hour : hour
        minute = minute < 10 ? '0' + minute : minute
        second = second < 10 ? '0' + second : second

        return day + '/' + month + '/' + year + ' ' + hour + ':' + minute + ':' + second
    }

    function tsGetHours(ts) {
        let date = new Date(ts)
        return date.getHours()
    }

    function classifyWindDir(value) {
        if (1 <= value && value < 90) {
            return "Timur Laut (TL)";
        } else if (value === 90) {
            return "Timur (T)";
        } else if (90 < value && value < 180) {
            return "Tenggara (TG)";
        } else if (value === 180) {
            return "Selatan (S)";
        } else if (180 < value && value < 270) {
            return "Barat Daya (BD)";
        } else if (value === 270) {
            return "Barat (B)";
        } else if (270 < value && value <= 360) {
            return "Barat Laut (BL)";
        } else {
            return "Utara (U)";
        }
    }

})