document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const packSelect = document.getElementById('packSelect');
  const selectedPackInput = document.getElementById('selectedPackInput');
  const packPriceInput = document.getElementById('packPriceInput');
  const summaryPackTitle = document.getElementById('summaryPackTitle');
  const summaryPrice = document.getElementById('summaryPrice');
  const selectPackButtons = document.querySelectorAll('.select-pack-btn');
  const orderForm = document.getElementById('orderForm');
  const submitBtn = document.getElementById('submitBtn');
  const btnText = submitBtn ? submitBtn.querySelector('.btn-text') : null;
  const btnLoader = submitBtn ? submitBtn.querySelector('.btn-loader') : null;
  const phoneInput = document.getElementById('userPhone');
  const carrierSelect = document.getElementById('carrierSelect');
  const cityInput = document.getElementById('userCity');
  const branchInput = document.getElementById('userBranch');
  const patronymicInput = document.getElementById('userPatronymic');
  const streetInput = document.getElementById('userStreet');
  const houseInput = document.getElementById('userHouse');
  const flatInput = document.getElementById('userFlat');
  const citySuggestions = document.getElementById('citySuggestions');
  const branchSuggestions = document.getElementById('branchSuggestions');
  const branchGroup = document.getElementById('branchGroup');
  const addressGroup = document.getElementById('addressGroup');
  const patronymicGroup = document.getElementById('patronymicGroup');
  const carrierGroup = document.getElementById('carrierGroup');
  const deliveryTypeGroup = document.getElementById('deliveryTypeGroup');
  const cityGroup = document.getElementById('cityGroup');
  const paymentGroup = document.getElementById('paymentGroup');
  const commentGroup = document.getElementById('commentGroup');
  const deliveryTypeInputs = document.querySelectorAll('input[name="deliveryType"]');
  let selectedCityRef = '';
  let selectedBranch = '';
  const successModal = document.getElementById('successModal');
  const modalDetails = document.getElementById('modalDetails');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const modalOverlay = document.getElementById('modalOverlay');

  function track(name, params) {
    if (typeof window.gtag === 'function') {
      try { window.gtag('event', name, params || {}); } catch (e) {}
    }
  }

  /* ==========================================================================
     1. Pack Selection Synchronization
     ========================================================================== */
  function updateOrderSummary(packId, customTitle, price) {
    const packSelect = document.getElementById('packSelect');
    if (packSelect) {
      packSelect.value = packId;
    }

    const selectedOption = packSelect && packSelect.options ? packSelect.options[packSelect.selectedIndex] : null;
    const title = customTitle || (selectedOption ? selectedOption.textContent : '');
    const finalPrice = price || (selectedOption ? selectedOption.getAttribute('data-price') : '');

    if (summaryPackTitle) summaryPackTitle.textContent = title;
    if (summaryPrice) summaryPrice.textContent = `${finalPrice} грн`;
    if (selectedPackInput) selectedPackInput.value = title;
    if (packPriceInput) packPriceInput.value = finalPrice;

    // Highlight selected card visually
    document.querySelectorAll('.pack-card').forEach(card => {
      if (card.getAttribute('data-pack-id') === String(packId)) {
        card.classList.add('pack-card--selected');
      } else {
        card.classList.remove('pack-card--selected');
      }
    });
  }

  // When user changes select in form
  if (packSelect) {
    packSelect.addEventListener('change', (e) => {
      const selectedOption = packSelect.options[packSelect.selectedIndex];
      const price = selectedOption.getAttribute('data-price');
      updateOrderSummary(e.target.value, selectedOption.textContent, price);
    });
  }

  // When user clicks button in pricing tables
  selectPackButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const packId = btn.getAttribute('data-pack');
      const title = btn.getAttribute('data-title');
      const price = btn.getAttribute('data-price');

      track('select_pack', { pack_id: packId, price: Number(price) || 0 });

      // Add to cart
      if (window.TeploCart && btn.hasAttribute('data-cart-id')) {
        window.TeploCart.add({
          id: btn.getAttribute('data-cart-id'),
          title: btn.getAttribute('data-cart-title'),
          price: btn.getAttribute('data-cart-price'),
          qty: 1
        });
      }

      updateOrderSummary(packId, title, price);

      const orderSection = document.getElementById('order');
      if (orderSection) {
        orderSection.scrollIntoView({ behavior: 'smooth' });
        // Focus name field slightly after scrolling
        setTimeout(() => {
          const nameInput = document.getElementById('userName');
          if (nameInput) nameInput.focus();
        }, 600);
      }
    });
  });

  // Whole pack card clickable -> product page
  const packProductUrls = {
    '1': 'product-try.html',
    '2': 'product-duo.html',
    '4': 'product-family.html'
  };
  document.querySelectorAll('.pack-card').forEach(card => {
    card.addEventListener('click', (e) => {
      if (e.target.closest('button, a, input')) return;
      const id = card.getAttribute('data-pack-id');
      const url = packProductUrls[id];
      if (url) window.location.href = url;
    });
  });

  // Prevent card navigation when clicking "Обрати" button
  selectPackButtons.forEach(btn => {
    btn.addEventListener('click', (e) => e.stopPropagation());
  });

  if (phoneInput) {
    phoneInput.addEventListener('focus', () => {
      if (!phoneInput.value) {
        phoneInput.value = '+380 ';
      }
    });

    phoneInput.addEventListener('input', () => {
      let digits = phoneInput.value.replace(/\D/g, '');

      if (digits.startsWith('380')) {
        // Вже з кодом країни
      } else if (digits.startsWith('80')) {
        digits = '3' + digits;
      } else if (digits.startsWith('0')) {
        digits = '38' + digits;
      } else {
        digits = '380' + digits;
      }

      // Формат: +380 (XX) XXX-XX-XX
      const body = digits.substring(3, 12);
      let formatted = '+380';

      if (body.length > 0) {
        formatted += ' (' + body.substring(0, 2);
      }
      if (body.length >= 2) {
        formatted += ') ' + body.substring(2, 5);
      }
      if (body.length >= 5) {
        formatted += '-' + body.substring(5, 7);
      }
      if (body.length >= 7) {
        formatted += '-' + body.substring(7, 9);
      }

      phoneInput.value = formatted;
    });
  }

  /* ==========================================================================
     3. Countdown Timer
     ========================================================================== */
  function startCountdown() {
    const hoursEl = document.getElementById('hours');
    const minutesEl = document.getElementById('minutes');
    const secondsEl = document.getElementById('seconds');

    if (!hoursEl || !minutesEl || !secondsEl) return;

    let totalSeconds = 4 * 3600 + 32 * 60 + 18;

    setInterval(() => {
      if (totalSeconds <= 0) {
        totalSeconds = 6 * 3600; // Reset timer for urgency
      }
      totalSeconds--;

      const h = Math.floor(totalSeconds / 3600);
      const m = Math.floor((totalSeconds % 3600) / 60);
      const s = totalSeconds % 60;

      hoursEl.textContent = String(h).padStart(2, '0');
      minutesEl.textContent = String(m).padStart(2, '0');
      secondsEl.textContent = String(s).padStart(2, '0');
    }, 1000);
  }
  startCountdown();

  /* ==========================================================================
     4. Interactive Warmer Graphic Animation
     ========================================================================== */
  const warmerBody = document.querySelector('.warmer-body');
  if (warmerBody) {
    warmerBody.addEventListener('click', () => {
      warmerBody.style.transform = 'scale(0.96)';
      setTimeout(() => {
        warmerBody.style.transform = 'scale(1.05)';
        setTimeout(() => {
          warmerBody.style.transform = '';
        }, 200);
      }, 100);
    });
  }

  /* ==========================================================================
     4b. Nova Poshta / Delengine autocomplete (cities & branches)
     ========================================================================== */
  // Load carriers
  (async () => {
    if (!carrierSelect) return;
    try {
      const resp = await fetch(`${npApiBase()}/api/np/companies`, { headers: npHeaders() });
      const data = await resp.json();
      if (!data.success) throw new Error(data.message);
      const items = data.items || [];
      carrierSelect.innerHTML = '';
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = 'Обрати перевізника';
      placeholder.selected = true;
      carrierSelect.appendChild(placeholder);
      items.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.uuid;
        opt.textContent = c.name;
        carrierSelect.appendChild(opt);
      });
    } catch (err) {
      carrierSelect.innerHTML = '<option value="">Усі перевізники</option>';
    }
  })();

  function getCarrierUuid() { return carrierSelect ? carrierSelect.value : ''; }
  function getCarrierName() {
    if (!carrierSelect) return '';
    const opt = carrierSelect.options[carrierSelect.selectedIndex];
    return opt ? opt.textContent.trim() : '';
  }
  function npApiBase() {
    const cfg = window.CONFIG || {};
    return (cfg.BOT_API_URL || '').replace(/\/api\/order\/?$/, '');
  }

  function npHeaders() {
    const cfg = window.CONFIG || {};
    return {
      'Content-Type': 'application/json',
      'X-API-Key': cfg.BOT_API_KEY || ''
    };
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  function showSuggestions(container, items, onPick) {
    if (!container) return;
    container.innerHTML = '';
    if (!items || !items.length) {
      const empty = document.createElement('div');
      empty.className = 'autocomplete-empty';
      empty.textContent = 'Не знайдено. Можна ввести вручну.';
      container.appendChild(empty);
      container.classList.add('is-open');
      return;
    }
    items.forEach(item => {
      const div = document.createElement('div');
      div.className = 'autocomplete-item';
      div.innerHTML = escapeHtml(item.label || item.name) + (item.sub ? `<small>${escapeHtml(item.sub)}</small>` : '');
      div.addEventListener('click', () => {
        onPick(item);
        container.classList.remove('is-open');
      });
      container.appendChild(div);
    });
    container.classList.add('is-open');
  }

  function hideSuggestions(container) {
    if (container) container.classList.remove('is-open');
  }

  // City search
  const cityCache = new Map();
  const branchCache = new Map();
  const searchCities = debounce(async (q) => {
    if (!q || q.length < 2) { hideSuggestions(citySuggestions); return; }
    const cacheKey = q.toLowerCase();
    if (cityCache.has(cacheKey)) {
      const items = cityCache.get(cacheKey);
      showSuggestions(citySuggestions, items, (item) => {
        if (cityInput) cityInput.value = item.label;
        selectedCityRef = item.ref;
        if (branchInput) {
          branchInput.value = '';
          branchInput.placeholder = 'Завантаження відділень…';
        }
        loadBranches(item.ref);
        updateStepVisibility();
      });
      return;
    }
    try {
      const resp = await fetch(`${npApiBase()}/api/np/cities?q=${encodeURIComponent(q)}`, { headers: npHeaders() });
      const data = await resp.json();
      if (!data.success) throw new Error(data.message);
      const items = (data.items || []).map(c => ({
        ref: c.ref,
        label: [c.type, c.name].filter(Boolean).join(' '),
        sub: c.area || '',
        raw: c
      }));
      cityCache.set(cacheKey, items);
      showSuggestions(citySuggestions, items, (item) => {
        if (cityInput) cityInput.value = item.label;
        selectedCityRef = item.ref;
        if (branchInput) {
          branchInput.value = '';
          branchInput.placeholder = 'Завантаження відділень…';
        }
        loadBranches(item.ref);
         updateStepVisibility();
      });
    } catch (err) {
      // Fallback: allow manual city entry
      hideSuggestions(citySuggestions);
    }
  }, 300);

  if (cityInput) {
    cityInput.addEventListener('input', (e) => {
      selectedCityRef = '';
      if (branchInput) branchInput.value = '';
      searchCities(e.target.value.trim());
    });
    cityInput.addEventListener('blur', () => setTimeout(() => hideSuggestions(citySuggestions), 200));
  }

  async function loadBranches(cityRef) {
    if (!cityRef || !branchInput) return;
    const type = getDeliveryType();
    const kind = type === 'postomat' ? 'postomat' : 'branch';
    const companyUuid = getCarrierUuid();
    const cacheKey = cityRef + '|' + kind + '|' + companyUuid;
    if (branchCache.has(cacheKey)) {
      const items = branchCache.get(cacheKey);
      branchInput.placeholder = items.length ? 'Оберіть відділення…' : 'Відділень не знайдено — введіть вручну';
      branchInput._items = items;
      if (items.length) {
        showSuggestions(branchSuggestions, items, (item) => {
          branchInput.value = item.label;
          selectedBranch = item.label;
          updateStepVisibility();
        });
      }
      return;
    }
    try {
      const url = `${npApiBase()}/api/np/warehouses?city_ref=${encodeURIComponent(cityRef)}&kind=${kind}${companyUuid ? '&company_uuid=' + encodeURIComponent(companyUuid) : ''}`;
      const resp = await fetch(url, { headers: npHeaders() });
      const data = await resp.json();
      if (!data.success) throw new Error(data.message);
      const items = (data.items || []).map(w => ({
        ref: w.ref,
        label: w.description || `№${w.number}`,
        sub: w.type || '',
        raw: w
      }));
      branchCache.set(cacheKey, items);
      branchInput.placeholder = items.length ? 'Оберіть відділення…' : 'Відділень не знайдено — введіть вручну';
      // store items for filtering
      branchInput._items = items;
      if (items.length) {
        showSuggestions(branchSuggestions, items, (item) => {
          branchInput.value = item.label;
          selectedBranch = item.label;
          updateStepVisibility();
        });
      }
    } catch (err) {
      branchInput.placeholder = 'Введіть відділення вручну';
    }
  }

  if (branchInput) {
    branchInput.addEventListener('input', (e) => {
      selectedBranch = '';
      const items = branchInput._items || [];
      const q = e.target.value.trim().toLowerCase();
      const filtered = q ? items.filter(i => i.label.toLowerCase().includes(q)) : items;
      showSuggestions(branchSuggestions, filtered, (item) => {
        branchInput.value = item.label;
        selectedBranch = item.label;
          updateStepVisibility();
      });
    });
    branchInput.addEventListener('focus', () => {
      const items = branchInput._items || [];
      if (items.length) showSuggestions(branchSuggestions, items, (item) => {
        branchInput.value = item.label;
        selectedBranch = item.label;
          updateStepVisibility();
      });
    });
    branchInput.addEventListener('blur', () => setTimeout(() => hideSuggestions(branchSuggestions), 200));
  }

  function getDeliveryType() {
    const checked = document.querySelector('input[name="deliveryType"]:checked');
    return checked ? checked.value : 'branch';
  }

  function toggleDeliveryFields() {
    const type = getDeliveryType();
    if (patronymicGroup) patronymicGroup.style.display = (type === 'address') ? '' : 'none';
    if (branchGroup) branchGroup.style.display = (type === 'address') ? 'none' : '';
    if (addressGroup) addressGroup.style.display = (type === 'address') ? '' : 'none';

    if (branchInput) {
      branchInput.required = (type !== 'address');
    }
    if (patronymicInput) {
      patronymicInput.required = (type === 'address');
    }
    if (streetInput) streetInput.required = (type === 'address');
    if (houseInput) houseInput.required = (type === 'address');

    // reload branches if city already selected and type changed
    if (selectedCityRef && type !== 'address') {
      loadBranches(selectedCityRef);
    }
  }

  if (carrierSelect) {
    carrierSelect.addEventListener('change', () => {
      if (selectedCityRef) loadBranches(selectedCityRef);
    });
  }

  /* ==========================================================================
     5. Order Submission to Telegram Bot
     ========================================================================== */
  if (orderForm) {
    let isSubmitting = false;

    orderForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (isSubmitting) return;

      const formData = new FormData(orderForm);
      const name = formData.get('name')?.toString().trim();
      const patronymic = (formData.get('patronymic') || '').toString().trim();
      const phone = formData.get('phone')?.toString().trim();
      const city = formData.get('city')?.toString().trim();
      const deliveryType = getDeliveryType();
      const branch = (formData.get('branch') || '').toString().trim();
      const street = (formData.get('street') || '').toString().trim();
      const house = (formData.get('house') || '').toString().trim();
      const flat = (formData.get('flat') || '').toString().trim();
      const payment = formData.get('payment')?.toString().trim();
      const comment = formData.get('comment')?.toString().trim() || '';
      // cart-aware
      let selectedPack, price, qty;
      if (window.TeploCart && !window.TeploCart.isEmpty()) {
        const items = window.TeploCart.get();
        selectedPack = items.map(i => i.title).join(' + ');
        price = window.TeploCart.total();
        qty = window.TeploCart.count();
      } else {
        selectedPack = selectedPackInput ? selectedPackInput.value : '2 шт (329 грн)';
        price = packPriceInput ? packPriceInput.value : '329';
        const m = (selectedPack || '').match(/(\d+)\s*шт/);
        qty = m ? Number(m[1]) : 1;
      }

      // Build delivery description
      let delivery = '';
      if (deliveryType === 'address') {
        if (!patronymic) {
          alert('Для адресної доставки вкажіть по батькові!');
          if (patronymicInput) patronymicInput.focus();
          isSubmitting = false;
          submitBtn.disabled = false;
          btnText.style.display = 'inline-flex';
          btnLoader.style.display = 'none';
          return;
        }
        if (!street || !house) {
          alert('Вкажіть вулицю та будинок для адресної доставки!');
          isSubmitting = false;
          submitBtn.disabled = false;
          btnText.style.display = 'inline-flex';
          btnLoader.style.display = 'none';
          return;
        }
        delivery = `Адресна доставка (${getCarrierName()}): ${street}, буд. ${house}${flat ? ', кв. ' + flat : ''}`;
      } else {
        if (!branch) {
          alert('Оберіть відділення / поштомат Нової Пошти!');
          if (branchInput) branchInput.focus();
          isSubmitting = false;
          submitBtn.disabled = false;
          btnText.style.display = 'inline-flex';
          btnLoader.style.display = 'none';
          return;
        }
        const prefix = deliveryType === 'postomat' ? 'Поштомат' : 'Відділення';
        delivery = `${getCarrierName()} — ${prefix}: ${branch}`;
      }

      // Validation
      if (!name || !phone || !city) {
        alert('Будь ласка, заповніть усі обов’язкові поля!');
        isSubmitting = false;
        submitBtn.disabled = false;
        btnText.style.display = 'inline-flex';
        btnLoader.style.display = 'none';
        return;
      }

      // Check phone length
      const digitsOnly = phone.replace(/\D/g, '');
      if (digitsOnly.length < 10) {
        alert('Будь ласка, введіть коректний номер телефону!');
        phoneInput.focus();
        return;
      }

      // Set Loading state
      isSubmitting = true;
      submitBtn.disabled = true;
      btnText.style.display = 'none';
      btnLoader.style.display = 'inline-flex';

      track('begin_checkout', { value: Number(price) || 0, currency: 'UAH', items: selectedPack });

      const orderDate = new Date().toLocaleString('uk-UA', {
        timeZone: 'Europe/Kyiv',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });

      // Prepare Telegram Message
      const messageText = `
🔥 <b>НОВЕ ЗАМОВЛЕННЯ — ТЕПЛОПАК</b> 🔥
━━━━━━━━━━━━━━━━━━━━
📦 <b>Комплект:</b> ${escapeHtml(selectedPack)}
💰 <b>До сплати:</b> <b>${escapeHtml(price)} грн</b>
━━━━━━━━━━━━━━━━━━━━
👤 <b>Клієнт:</b> ${escapeHtml(name)}${patronymic ? ' ' + escapeHtml(patronymic) : ''}
📞 <b>Телефон:</b> <a href="tel:${digitsOnly}">${escapeHtml(phone)}</a>
📍 <b>Місто:</b> ${escapeHtml(city)}
🚚 <b>Доставка:</b> ${escapeHtml(delivery)}
💳 <b>Оплата:</b> ${escapeHtml(payment)}
💬 <b>Коментар:</b> ${escapeHtml(comment || '—')}
⏰ <b>Час заявки:</b> ${orderDate}
━━━━━━━━━━━━━━━━━━━━
🌐 <i>Заявка з лендінгу</i>
      `.trim();

      let orderNumber = null;

      try {
        const cfg = window.CONFIG || {};

        if (cfg.USE_BOT_API) {
          // CRM-бот: замовлення створюється в базі, отримує номер і потрапляє в Telegram
          if (!cfg.BOT_API_URL) {
            throw new Error('Не вказано BOT_API_URL у js/config.js');
          }

          const botResponse = await fetch(cfg.BOT_API_URL, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': cfg.BOT_API_KEY || ''
            },
            body: JSON.stringify({
              name,
              patronymic,
              phone,
              city,
              delivery,
              payment,
              comment,
              pack: selectedPack,
              price: Number(price),
              qty,
              source: 'landing'
            })
          });

          const botData = await botResponse.json().catch(() => ({}));
          if (!botResponse.ok || !botData.success) {
            throw new Error(botData.message || 'Помилка сервера');
          }
          orderNumber = botData.order_number;
          track('purchase', { transaction_id: orderNumber, value: Number(price) || 0, currency: 'UAH' });        } else if (cfg.USE_PHP_BACKEND) {
          // Send via send.php
          const response = await fetch('send.php', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              name,
              patronymic,
              phone,
              city,
              delivery,
              payment,
              comment,
              selectedPack,
              price,
              date: orderDate
            })
          });

          const data = await response.json();
          if (!data.success) {
            throw new Error(data.message || 'Помилка сервера');
          }
        } else {
          // Пряма відправка в Telegram (без CRM)
          const token = cfg.TELEGRAM_BOT_TOKEN || '';
          const chatId = cfg.TELEGRAM_CHAT_ID || '';

          if (!token || token.includes('your-token-here')) {
            console.warn('Відправка не налаштована у js/config.js. Працює тестовий режим.');
            // Simulate network delay for demo
            await new Promise(res => setTimeout(res, 800));
          } else {
            const tgUrl = `https://api.telegram.org/bot${token}/sendMessage`;
            const response = await fetch(tgUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                chat_id: chatId,
                text: messageText,
                parse_mode: 'HTML',
                disable_web_page_preview: true
              })
            });

            const data = await response.json();
            if (!data.ok) {
              console.error('Telegram API Error:', data);
              throw new Error(data.description || 'Помилка Telegram API');
            }
          }
        }

        // Show Success Modal
        showSuccessModal({
          name,
          phone,
          pack: selectedPack,
          delivery,
          price: `${price} грн`,
          orderNumber
        });
        track('order_completed', { order_number: orderNumber, value: Number(price) || 0, currency: 'UAH' });

        // Reset form
        orderForm.reset();
        // Restore default select
        if (packSelect) updateOrderSummary(2, '2 шт — Комплект «Для двох рук» (329 грн)', '329');

      } catch (err) {
        console.error('Submission error:', err);
        track('order_error', { message: (err && err.message) ? err.message : 'unknown' });
        alert('Не вдалося надіслати замовлення 😔\n\nПеревірте з’єднання з інтернетом і спробуйте ще раз. Якщо помилка повторюється — зателефонуйте нам, і ми оформимо замовлення вручну.');
      } finally {
        isSubmitting = false;
        submitBtn.disabled = false;
        btnText.style.display = 'inline-flex';
        btnLoader.style.display = 'none';
      }
    });
  }

  /* ==========================================================================
     6. Hide mobile CTA while the order form is on screen
     ========================================================================== */
  const mobileCta = document.querySelector('.mobile-cta');
  const orderSection = document.getElementById('order');

  if (mobileCta && orderSection && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        mobileCta.classList.toggle('mobile-cta--hidden', entry.isIntersecting);
      });
    }, { threshold: 0.12 });

    observer.observe(orderSection);
  }

  /* ==========================================================================
     7. Modal Operations
     ========================================================================== */
  function showSuccessModal(data) {
    if (!successModal) return;

    if (modalDetails) {
      const numberRow = data.orderNumber
        ? `<div class="modal__details-row"><span>Номер замовлення:</span><strong>№${escapeHtml(data.orderNumber)}</strong></div>`
        : '';

      modalDetails.innerHTML = numberRow + `
        <div class="modal__details-row">
          <span>Одержувач:</span>
          <strong>${escapeHtml(data.name)}</strong>
        </div>
        <div class="modal__details-row">
          <span>Телефон:</span>
          <strong>${escapeHtml(data.phone)}</strong>
        </div>
        <div class="modal__details-row">
          <span>Товар:</span>
          <strong>${escapeHtml(data.pack)}</strong>
        </div>
        <div class="modal__details-row">
          <span>Доставка:</span>
          <strong>${escapeHtml(data.delivery)}</strong>
        </div>
        <div class="modal__details-row">
          <span>Сума:</span>
          <strong>${escapeHtml(data.price)}</strong>
        </div>
      `;
    }

    successModal.classList.add('is-active');
  }

  function closeModal() {
    if (successModal) {
      successModal.classList.remove('is-active');
    }
  }

  if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
  if (modalOverlay) modalOverlay.addEventListener('click', closeModal);

  // Close modal on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && successModal && successModal.classList.contains('is-active')) {
      closeModal();
    }
  });

  /* ==========================================================================
     Helper Functions
     ========================================================================== */
  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }


  // Progressive disclosure of delivery fields
  function updateStepVisibility() {
    var cityFilled = !!(cityInput && cityInput.value.trim().length >= 2);
    // city is always visible
    if (cityGroup) cityGroup.style.display = '';

    var carrierSelected = !!(carrierSelect && carrierSelect.value);
    if (carrierGroup) carrierGroup.style.display = cityFilled ? '' : 'none';

    var deliveryType = getDeliveryType();
    if (deliveryTypeGroup) deliveryTypeGroup.style.display = carrierSelected ? '' : 'none';

    if (deliveryType === 'address') {
      if (patronymicGroup) patronymicGroup.style.display = carrierSelected ? '' : 'none';
      if (addressGroup) addressGroup.style.display = (carrierSelected && cityFilled) ? '' : 'none';
      if (branchGroup) branchGroup.style.display = 'none';
    } else {
      if (patronymicGroup) patronymicGroup.style.display = 'none';
      if (addressGroup) addressGroup.style.display = 'none';
      if (branchGroup) branchGroup.style.display = (carrierSelected && cityFilled) ? '' : 'none';
    }

    var deliveryReady = false;
    if (deliveryType === 'address') {
      deliveryReady = cityFilled && carrierSelected && !!(streetInput && streetInput.value.trim()) && !!(houseInput && houseInput.value.trim()) && !!(patronymicInput && patronymicInput.value.trim());
    } else {
      deliveryReady = cityFilled && carrierSelected && !!(branchInput && branchInput.value.trim());
    }
    if (paymentGroup) paymentGroup.style.display = deliveryReady ? '' : 'none';
    if (commentGroup) commentGroup.style.display = deliveryReady ? '' : 'none';
  }

  if (carrierSelect) carrierSelect.addEventListener('change', function(){ if (selectedCityRef) loadBranches(selectedCityRef); updateStepVisibility(); });
  if (cityInput) cityInput.addEventListener('input', updateStepVisibility);
  if (branchInput) branchInput.addEventListener('input', updateStepVisibility);
  if (streetInput) streetInput.addEventListener('input', updateStepVisibility);
  if (houseInput) houseInput.addEventListener('input', updateStepVisibility);
  if (patronymicInput) patronymicInput.addEventListener('input', updateStepVisibility);
  if (deliveryTypeInputs) deliveryTypeInputs.forEach(function(r){ r.addEventListener('change', function(){ track('select_delivery_type', { type: getDeliveryType() }); toggleDeliveryFields(); updateStepVisibility(); }); });
  updateStepVisibility();


  // Preselect pack from URL (?pack=1|2|4)
  const urlParams = new URLSearchParams(window.location.search);
  const packParam = urlParams.get('pack');
  if (packParam && ['1','2','4'].includes(packParam)) {
    const btn = document.querySelector('.select-pack-btn[data-pack="' + packParam + '"]');
    if (btn) btn.click();
  }

});
