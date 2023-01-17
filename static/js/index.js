let graphCount = 0
let graphCounta = 0
let graphCountb = 0
let current = '#chart-container'
let currenta = '#chart-container'
let currentb = '#chart-container'

let containerCount = 0
let containerCounta = 0
let containerCountb = 0



// Our data source for first line
const line1Data = [
[0.0, -5.551115123125783e-16],
[0.05263157894736842, 0.3847721996036613],
[0.10526315789473684, 0.6317255635926372],
[0.15789473684210525, 0.7811810013907878],
[0.21052631578947367, 0.8636224074487105],
[0.2631578947368421, 0.901385744528839],
[0.3157894736842105, 0.9101886473157371],
[0.3684210526315789, 0.900500546351585],
[0.42105263157894735, 0.87875331229686],
[0.47368421052631576, 0.8483924205162098],
[0.5263157894736842, 0.8107686359895193],
[0.5789473684210527, 0.7658702185481715],
[0.631578947368421, 0.712895648436501],
[0.6842105263157894, 0.6506668721984405],
[0.7368421052631579, 0.5778830688893626],
[0.7894736842105263, 0.49321493661311233],
[0.8421052631578947, 0.39523949938423597],
[0.894736842105263, 0.28221543431539997],
[0.9473684210526315, 0.15169891913000644],
[1.0, 2.220446049250313e-16]
];

// Generate an svg path 
function generateSvgPath(data, appender) {
let randcolor = getRandomColor();
let svgPath = `<path style="stroke:${randcolor}" class="chart-line${appender}" d="`
let startCP;
let endCP;
data.forEach((dot, i) => {
    if (i !== 0) {
    startCP = controlPoint(data[i - 1], data[i - 2], dot);
    endCP = controlPoint(dot, data[i - 1], data[i + 1], true);
    }
    svgPath += i === 0 ? 'M ' : 'C ';
    svgPath += i === 0 ? `${dot[0]},${dot[1]} ` : `${startCP.x},${startCP.y} ${endCP.x},${endCP.y} ${dot[0]},${dot[1]} `
})
// Close the chart for filling color
svgPath += `"></path>`
return svgPath;
}

// Get length and angle between two points
// Reference: https://medium.com/@francoisromain/smooth-a-svg-path-with-cubic-bezier-curves-e37b49d46c74
const line = (pointA, pointB) => {
const lengthX = pointB[0] - pointA[0]
const lengthY = pointB[1] - pointA[1]
return {
    length: Math.sqrt(Math.pow(lengthX, 2) + Math.pow(lengthY, 2)),
    angle: Math.atan2(lengthY, lengthX)
}
}

// Get a control point for curve line
// Reference: https://medium.com/@francoisromain/smooth-a-svg-path-with-cubic-bezier-curves-e37b49d46c74
const controlPoint = (current, previous, next, reverse) => {
const p = previous || current
const n = next || current
const smoothing = 0.15
const o = line(p, n)
const angle = o.angle + (reverse ? Math.PI : 0)
const length = o.length * smoothing
const x = current[0] + Math.cos(angle) * length
const y = current[1] + Math.sin(angle) * length
return {x, y};
}

const addLineToSVG = (data, color, multiplier, current, appender) => {
data = data.map(item => [item[0] * multiplier, item[1] * multiplier]);
let line = generateSvgPath(data, appender);
$(current).append(line);
$(current).html($(current).html());
}

window.setInterval(() => {
    for (let i = 0; i < 8; i++){
        let multiplier = Math.floor(Math.random() * 250);
        addLineToSVG(line1Data, 'primary', multiplier, current, "");
    }
    let randX = randXgenerator();
    let randY = randYgenerator();
    $('#svgBox').append(`<svg overflow ="visible" width = "200" height = "200" viewBox = " ${randX} ${randY} 400 400" class="svg-container"><g id='chart-container` + containerCount + `'></g></svg>`)
    current = '#chart-container' + containerCount
    containerCount++;
    graphCount = 0;
}, 750);

/*
window.setInterval(() => {
    for (let i = 0; i < 8; i++){
        let multiplier = Math.floor(Math.random() * 250);
        addLineToSVG(line1Data, 'primary', multiplier, currenta, "a");
        graphCounta++;
    }
        let randX = randXgenerator();
        let randY = randYgenerator();
        $('#svgBox').append(`<svg overflow = "visible" width = "200" height = "200" viewBox = " ${randX} ${randY} 500 500" class="svg-container"><g id='chart-container-a` + containerCounta + `'></g></svg>`)
        currenta = '#chart-container-a' + containerCounta
        containerCounta++;
        graphCounta = 0;
}, 1000 + Math.floor(Math.random() * 500));
*/
/*
window.setInterval(() => {
    for (let i = 0; i < 8; i++){
        let multiplier = Math.floor(Math.random() * 250);
        addLineToSVG(line1Data, 'primary', multiplier, currentb, "b");
        graphCountb++;
    }
        let randX = randXgenerator();
        let randY = randYgenerator();
        $('#svgBox').append(`<svg overflow = "visible" width = "200" height = "200" viewBox = " ${randX} ${randY} 500 500" class="svg-container"><g id='chart-container-b` + containerCountb + `'></g></svg>`)
        currentb = '#chart-container-b' + containerCountb
        containerCountb++;
        graphCountb = 0;
}, 500 + Math.floor(Math.random() * 500));
*/
function randXgenerator(){
    let randX = 0;
    return randX;
}

function randYgenerator(){
    let randY =  0;
    return randY;
}


function getRandomColor() {
var letters = '0123456789ABCDEF';
var color = '#';
for (var i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
}
return color;
}