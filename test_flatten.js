const fs = require('fs');
let centroid = [0, 0];
let count = 0;
const flatten = (arr) => {
    if (typeof arr[0] === 'number') {
        centroid[0] += arr[0];
        centroid[1] += arr[1];
        count++;
    } else {
        arr.forEach(flatten);
    }
};

const data = JSON.parse(require('child_process').execSync('curl -s "http://localhost/api/geo/collections/public.vw_gebieden_features/items?limit=1"'));
const coords = data.features[0].geometry.coordinates;
flatten(coords);
if (count > 0) {
    centroid[0] /= count;
    centroid[1] /= count;
}
console.log(centroid, count);
