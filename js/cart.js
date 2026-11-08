// js/cart.js — спільна логіка кошика (localStorage)
(function () {
  const KEY = 'teplopak_cart';

  function getCart() {
    try { return JSON.parse(localStorage.getItem(KEY)) || []; }
    catch (e) { return []; }
  }
  function saveCart(cart) {
    localStorage.setItem(KEY, JSON.stringify(cart));
    updateBadge();
    window.dispatchEvent(new CustomEvent('cart:changed', { detail: cart }));
  }
  function addItem(item) {
    const cart = getCart();
    const existing = cart.find(x => x.id === item.id);
    if (existing) existing.qty += item.qty || 1;
    else cart.push({ id: item.id, title: item.title, price: Number(item.price) || 0, qty: item.qty || 1 });
    saveCart(cart);
  }
  function updateQty(id, qty) {
    const cart = getCart();
    const it = cart.find(x => x.id === id);
    if (!it) return;
    it.qty = Math.max(1, qty);
    saveCart(cart);
  }
  function removeItem(id) {
    saveCart(getCart().filter(x => x.id !== id));
  }
  function clearCart() { saveCart([]); }
  function totalCount() { return getCart().reduce((s, x) => s + x.qty, 0); }
  function totalPrice() { return getCart().reduce((s, x) => s + x.price * x.qty, 0); }
  function isEmpty() { return getCart().length === 0; }

  function updateBadge() {
    const badges = document.querySelectorAll('.cart-badge');
    const count = totalCount();
    badges.forEach(b => {
      b.textContent = count;
      b.style.display = count > 0 ? 'inline-flex' : 'none';
    });
  }

  window.TeploCart = {
    get: getCart, save: saveCart, add: addItem, updateQty, remove: removeItem,
    clear: clearCart, count: totalCount, total: totalPrice, isEmpty
  };

  document.addEventListener('DOMContentLoaded', updateBadge);
})();
