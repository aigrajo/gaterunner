(() => {
  for (const s of ['Accelerometer','Gyroscope','GravitySensor',
                   'LinearAccelerationSensor','AbsoluteOrientationSensor',
                   'RelativeOrientationSensor']) {
    if (self[s]) self[s] = () => { throw new DOMException('blocked','SecurityError'); };
  }
})();
