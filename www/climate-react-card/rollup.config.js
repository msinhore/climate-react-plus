// File: www/climate-react-card/rollup.config.js
import resolve from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";
import typescript from "@rollup/plugin-typescript";
import terser from "@rollup/plugin-terser";

export default {
  input: "climate-react-card.ts",
  output: {
    file: "dist/climate-react-card.js",
    format: "es",
    sourcemap: false,
  },
  plugins: [resolve(), commonjs(), typescript({ tsconfig: "./tsconfig.json" }), terser()],
};
