import resolve from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";
import typescript from "@rollup/plugin-typescript";
import terser from "@rollup/plugin-terser";

export default {
  input: "thermoadapt-card.ts",          // ⟵  novo nome do entry-point
  output: {
    dir: "dist",
    format: "es",
    entryFileNames: "thermoadapt-card.js",
    sourcemap: false,
  },
  plugins: [
    resolve(),
    commonjs(),
    typescript({ tsconfig: "./tsconfig.json" }),
    terser(),                            // minify bundle
  ],
};
