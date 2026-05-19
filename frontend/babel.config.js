module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    // react-native-worklets/plugin habilita los worklets de Reanimated 4
    // (drawer, gestos). DEBE ser el último plugin de la lista.
    plugins: ["react-native-worklets/plugin"],
  };
};
