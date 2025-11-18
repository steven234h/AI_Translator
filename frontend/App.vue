<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App',
  onLaunch: function() {
    console.log('App Launch')
  },
  onShow: function() {
    console.log('App Show')
  },
  onHide: function() {
    console.log('App Hide')
  }
}
</script>

<style>
/* 每个页面公共css */
:root {
  --brand-start: #a3bffa;
  --brand-end: #b794f4;
  --text-strong: #333333;
  --text-subtle: #666666;
  --surface: #ffffff;
  --surface-weak: #f5f7ff;
  --border-weak: #a5b4fc;
}

/* 字体与渲染优化 */
html, body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
